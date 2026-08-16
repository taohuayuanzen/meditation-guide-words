[CmdletBinding(DefaultParameterSetName = 'DryRun')]
param(
    [Parameter(ParameterSetName = 'Apply')]
    [switch]$Apply,

    [Parameter(ParameterSetName = 'Verify')]
    [switch]$VerifyOnly,

    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$AppId = 'b9f7e107-3684-488e-9850-ca0ed1d25fef',

    [string]$DbContainer = 'docker-db_postgres-1',
    [string]$Database = 'dify',
    [string]$DatabaseUser = 'postgres'
)

$ErrorActionPreference = 'Stop'

$dockerBin = 'C:\Program Files\Docker\Docker\resources\bin'
if (Test-Path -LiteralPath $dockerBin) {
    $env:Path = "$dockerBin;$env:Path"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backupDir = Join-Path $repoRoot 'data\dify-backups'

function Invoke-DifyPsql {
    param(
        [Parameter(Mandatory)]
        [string]$Sql,
        [switch]$TuplesOnly
    )

    $arguments = @('exec', $DbContainer, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', $DatabaseUser, '-d', $Database, '-P', 'pager=off')
    if ($TuplesOnly) {
        $arguments += @('-A', '-t')
    }
    $arguments += @('-c', $Sql)

    $output = & docker @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($output -join [Environment]::NewLine)
    }
    return $output
}

function Get-WorkflowSummarySql {
    return @"
SELECT
    w.id AS workflow_id,
    w.version,
    w.updated_at,
    jsonb_array_length(w.graph::jsonb->'nodes') AS node_count,
    jsonb_array_length(w.graph::jsonb->'edges') AS edge_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'nodes') n WHERE n->'data'->>'type' = 'start') AS start_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'nodes') n WHERE n->'data'->>'type' = 'llm') AS llm_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'nodes') n WHERE n->'data'->>'type' = 'answer') AS answer_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'nodes') n WHERE n->'data'->>'type' = 'end') AS end_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'nodes') n
      WHERE n->'data'->>'type' = 'start' AND n->>'type' = 'custom') AS custom_start_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'nodes') n
      WHERE n->'data'->>'type' = 'end' AND n->>'type' = 'custom') AS custom_end_count,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'edges') e
      WHERE e->'data'->>'sourceType' = 'start'
        AND e->'data'->>'targetType' = 'llm'
        AND e->>'sourceHandle' = 'source'
        AND e->>'targetHandle' = 'target') AS valid_start_llm_edges,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'edges') e
      WHERE e->'data'->>'sourceType' = 'llm'
        AND e->'data'->>'targetType' = 'answer'
        AND e->>'sourceHandle' = 'source'
        AND e->>'targetHandle' = 'target') AS valid_llm_answer_edges,
    (SELECT count(*) FROM jsonb_array_elements(w.graph::jsonb->'edges') e
      WHERE e->'data'->>'sourceType' = 'answer'
        AND e->'data'->>'targetType' = 'end'
        AND e->>'sourceHandle' = 'source'
        AND e->>'targetHandle' = 'target') AS valid_answer_end_edges
FROM workflows w
WHERE w.app_id = '$AppId'::uuid AND w.version = 'draft';
"@
}

Write-Host "Dify App: $AppId"
Write-Host 'Current draft summary:'
Invoke-DifyPsql -Sql (Get-WorkflowSummarySql)

if ($VerifyOnly) {
    $verificationSql = @"
SELECT CASE WHEN
    (SELECT count(*) FROM workflows WHERE app_id = '$AppId'::uuid AND version = 'draft') = 1
    AND (SELECT count(*) FROM workflows w CROSS JOIN LATERAL jsonb_array_elements(w.graph::jsonb->'nodes') n
         WHERE w.app_id = '$AppId'::uuid AND w.version = 'draft'
           AND n->'data'->>'type' = 'start' AND n->>'type' = 'custom') = 1
    AND (SELECT count(*) FROM workflows w CROSS JOIN LATERAL jsonb_array_elements(w.graph::jsonb->'nodes') n
         WHERE w.app_id = '$AppId'::uuid AND w.version = 'draft'
           AND n->'data'->>'type' = 'end' AND n->>'type' = 'custom') = 1
    AND (SELECT count(*) FROM workflows w CROSS JOIN LATERAL jsonb_array_elements(w.graph::jsonb->'edges') e
         WHERE w.app_id = '$AppId'::uuid AND w.version = 'draft'
           AND e->'data'->>'sourceType' = 'start' AND e->'data'->>'targetType' = 'llm'
           AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target') = 1
    AND (SELECT count(*) FROM workflows w CROSS JOIN LATERAL jsonb_array_elements(w.graph::jsonb->'edges') e
         WHERE w.app_id = '$AppId'::uuid AND w.version = 'draft'
           AND e->'data'->>'sourceType' = 'llm' AND e->'data'->>'targetType' = 'answer'
           AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target') = 1
    AND (SELECT count(*) FROM workflows w CROSS JOIN LATERAL jsonb_array_elements(w.graph::jsonb->'edges') e
         WHERE w.app_id = '$AppId'::uuid AND w.version = 'draft'
           AND e->'data'->>'sourceType' = 'answer' AND e->'data'->>'targetType' = 'end'
           AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target') = 1
THEN 'PASS' ELSE 'FAIL' END AS verification;
"@
    $verification = (Invoke-DifyPsql -Sql $verificationSql -TuplesOnly | Out-String).Trim()
    if ($verification -ne 'PASS') {
        throw 'Draft verification failed.'
    }
    Write-Host 'Verification: PASS' -ForegroundColor Green
    exit 0
}

if (-not $Apply) {
    Write-Host ''
    Write-Host 'Dry-run only. Planned changes:' -ForegroundColor Yellow
    Write-Host '1. Normalize the start -> LLM edge to sourceHandle=source and targetHandle=target.'
    Write-Host '2. Normalize the top-level React Flow type of Start and End to custom.'
    Write-Host '3. Add one End node if it is missing.'
    Write-Host '4. Add Answer -> End with source/target handles if it is missing.'
    Write-Host '5. Leave all existing Start, LLM, and Answer node data unchanged.'
    Write-Host ''
    Write-Host 'Run again with -Apply to back up and repair the draft.'
    exit 0
}

Write-Warning 'Before continuing, close every browser tab that has this Dify workflow editor open.'
Write-Warning 'An open editor can auto-save its stale in-memory graph and overwrite the repair.'

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupPath = Join-Path $backupDir "workflow-$AppId-draft-$timestamp.json"
$encodedGraphSql = "SELECT encode(convert_to(graph, 'UTF8'), 'base64') FROM workflows WHERE app_id = '$AppId'::uuid AND version = 'draft';"
$encodedGraph = ((Invoke-DifyPsql -Sql $encodedGraphSql -TuplesOnly) -join '').Trim()
if ([string]::IsNullOrWhiteSpace($encodedGraph)) {
    throw 'Draft graph was not found; no changes were made.'
}
[IO.File]::WriteAllBytes($backupPath, [Convert]::FromBase64String($encodedGraph))
Write-Host "Backup created: $backupPath"

$endNodeId = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds().ToString()

$repairSql = @"
BEGIN;

DO `$repair`$
DECLARE
    workflow_count integer;
    start_count integer;
    llm_count integer;
    answer_count integer;
    start_edge_count integer;
    llm_answer_edge_count integer;
    draft_graph jsonb;
    repaired_nodes jsonb;
    repaired_edges jsonb;
    start_id text;
    llm_id text;
    answer_id text;
    end_id text;
    answer_x numeric;
    answer_y numeric;
BEGIN
    SELECT count(*) INTO workflow_count
    FROM workflows
    WHERE app_id = '$AppId'::uuid AND version = 'draft';
    IF workflow_count <> 1 THEN
        RAISE EXCEPTION 'Expected exactly one draft workflow, found %', workflow_count;
    END IF;

    SELECT graph::jsonb INTO draft_graph
    FROM workflows
    WHERE app_id = '$AppId'::uuid AND version = 'draft'
    FOR UPDATE;

    SELECT count(*), min(n->>'id') INTO start_count, start_id
    FROM jsonb_array_elements(draft_graph->'nodes') n
    WHERE n->'data'->>'type' = 'start';
    SELECT count(*), min(n->>'id') INTO llm_count, llm_id
    FROM jsonb_array_elements(draft_graph->'nodes') n
    WHERE n->'data'->>'type' = 'llm';
    SELECT count(*), min(n->>'id') INTO answer_count, answer_id
    FROM jsonb_array_elements(draft_graph->'nodes') n
    WHERE n->'data'->>'type' = 'answer';

    IF start_count <> 1 OR llm_count <> 1 OR answer_count <> 1 THEN
        RAISE EXCEPTION 'Expected one start, one llm and one answer; found start=%, llm=%, answer=%',
            start_count, llm_count, answer_count;
    END IF;

    SELECT count(*) INTO start_edge_count
    FROM jsonb_array_elements(draft_graph->'edges') e
    WHERE e->>'source' = start_id AND e->>'target' = llm_id;
    SELECT count(*) INTO llm_answer_edge_count
    FROM jsonb_array_elements(draft_graph->'edges') e
    WHERE e->>'source' = llm_id AND e->>'target' = answer_id
      AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target';

    IF start_edge_count <> 1 OR llm_answer_edge_count <> 1 THEN
        RAISE EXCEPTION 'Expected one start->llm edge and one valid llm->answer edge; found % and %',
            start_edge_count, llm_answer_edge_count;
    END IF;

    SELECT n->'position'->>'x', n->'position'->>'y'
    INTO answer_x, answer_y
    FROM jsonb_array_elements(draft_graph->'nodes') n
    WHERE n->>'id' = answer_id;

    SELECT n->>'id' INTO end_id
    FROM jsonb_array_elements(draft_graph->'nodes') n
    WHERE n->'data'->>'type' = 'end'
    LIMIT 1;

    SELECT jsonb_agg(
        CASE WHEN n->'data'->>'type' = 'start' THEN
            jsonb_set(n, '{type}', to_jsonb('custom'::text))
        WHEN n->'data'->>'type' = 'end' THEN
            jsonb_set(
                jsonb_set(n, '{type}', to_jsonb('custom'::text)),
                '{data,title}',
                to_jsonb((chr(32467) || chr(26463))::text)
            )
        ELSE n END
    ) INTO repaired_nodes
    FROM jsonb_array_elements(draft_graph->'nodes') n;

    IF end_id IS NULL THEN
        end_id := '$endNodeId';
        repaired_nodes := repaired_nodes || jsonb_build_array(jsonb_build_object(
            'id', end_id,
            'type', 'custom',
            'data', jsonb_build_object(
                'type', 'end',
                'title', chr(32467) || chr(26463),
                'outputs', jsonb_build_array(jsonb_build_object(
                    'variable', 'result',
                    'value_selector', jsonb_build_array(llm_id, 'text')
                )),
                'selected', false
            ),
            'position', jsonb_build_object('x', COALESCE(answer_x, 0) + 320, 'y', COALESCE(answer_y, 0)),
            'positionAbsolute', jsonb_build_object('x', COALESCE(answer_x, 0) + 320, 'y', COALESCE(answer_y, 0)),
            'width', 150,
            'height', 22,
            'zIndex', 0,
            'selected', false
        ));
    END IF;

    SELECT jsonb_agg(
        CASE WHEN e->>'source' = start_id AND e->>'target' = llm_id THEN
            jsonb_set(
                jsonb_set(
                    jsonb_set(e, '{id}', to_jsonb(start_id || '-source-' || llm_id || '-target')),
                    '{sourceHandle}', to_jsonb('source'::text)
                ),
                '{targetHandle}', to_jsonb('target'::text)
            )
        ELSE e END
    ) INTO repaired_edges
    FROM jsonb_array_elements(draft_graph->'edges') e;

    IF NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(repaired_edges) e
        WHERE e->>'source' = answer_id AND e->>'target' = end_id
    ) THEN
        repaired_edges := repaired_edges || jsonb_build_array(jsonb_build_object(
            'id', answer_id || '-source-' || end_id || '-target',
            'type', 'custom',
            'source', answer_id,
            'target', end_id,
            'sourceHandle', 'source',
            'targetHandle', 'target',
            'zIndex', 0,
            'data', jsonb_build_object(
                'sourceType', 'answer',
                'targetType', 'end',
                'isInLoop', false,
                'isInIteration', false
            )
        ));
    END IF;

    draft_graph := jsonb_set(jsonb_set(draft_graph, '{nodes}', repaired_nodes), '{edges}', repaired_edges);

    IF NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(draft_graph->'nodes') n
        WHERE n->>'id' = start_id AND n->>'type' = 'custom' AND n->'data'->>'type' = 'start'
    ) OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(draft_graph->'nodes') n
        WHERE n->>'id' = end_id AND n->>'type' = 'custom' AND n->'data'->>'type' = 'end'
    ) OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(draft_graph->'edges') e
        WHERE e->>'source' = start_id AND e->>'target' = llm_id
          AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target'
    ) OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(draft_graph->'edges') e
        WHERE e->>'source' = llm_id AND e->>'target' = answer_id
          AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target'
    ) OR NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(draft_graph->'edges') e
        WHERE e->>'source' = answer_id AND e->>'target' = end_id
          AND e->>'sourceHandle' = 'source' AND e->>'targetHandle' = 'target'
    ) THEN
        RAISE EXCEPTION 'Repaired graph did not pass the complete-chain assertion';
    END IF;

    UPDATE workflows
    SET graph = draft_graph::text, updated_at = CURRENT_TIMESTAMP
    WHERE app_id = '$AppId'::uuid AND version = 'draft';
END
`$repair`$;

COMMIT;
"@

Invoke-DifyPsql -Sql $repairSql
Write-Host 'Draft repair completed.' -ForegroundColor Green
Write-Host 'Updated draft summary:'
Invoke-DifyPsql -Sql (Get-WorkflowSummarySql)
Write-Host 'Reload the Dify workflow page and confirm that the checklist is empty before publishing.' -ForegroundColor Yellow

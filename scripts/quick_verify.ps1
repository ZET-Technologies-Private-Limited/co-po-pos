$ErrorActionPreference='Continue'
$base='http://127.0.0.1:8011/api/v1'
$course='807f8f2c-9b75-4355-9800-e0a3edbcd58e'
$exam='ff7d7335-250d-4c97-922c-cc066f45dec9'
$program='BTECH-CSE-0e2ce4b3'
$results=@()

function Add($k,$s,$d){
  $script:results += [pscustomobject]@{check=$k;status=$s;detail=$d}
}

function TryCall($name,[scriptblock]$block){
  try {
    $r = & $block
    Add $name 'PASS' (($r | Out-String).Trim())
  } catch {
    $msg = if($_.ErrorDetails){$_.ErrorDetails.Message}else{$_.Exception.Message}
    Add $name 'FAIL' $msg
  }
}

$adm='adm_'+[guid]::NewGuid().ToString('N').Substring(0,6)
$areg=Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body (@{username=$adm;email="$adm@example.com";password='Pass@1234';full_name='Admin';role='admin'}|ConvertTo-Json -Compress)
$hA=@{Authorization="Bearer $($areg.access_token)"}
Add 'auth_admin' 'PASS' $areg.role

$fac='fac_'+[guid]::NewGuid().ToString('N').Substring(0,6)
$freg=Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body (@{username=$fac;email="$fac@example.com";password='Pass@1234';full_name='Faculty';role='faculty'}|ConvertTo-Json -Compress)
$hF=@{Authorization="Bearer $($freg.access_token)"}
Add 'auth_faculty' 'PASS' $freg.role

TryCall 'fn1_input_assets_available' {
  $po=((Invoke-RestMethod -Method Get -Uri "$base/programs/$program/outcomes" -Headers $hA).Count)
  $pso=((Invoke-RestMethod -Method Get -Uri "$base/programs/$program/pso" -Headers $hA).Count)
  $co=((Invoke-RestMethod -Method Get -Uri "$base/courses/$course/outcomes" -Headers $hA).Count)
  "po=$po,pso=$pso,co=$co"
}

TryCall 'fn2_exam_configuration_available' {
  $e=Invoke-RestMethod -Method Get -Uri "$base/courses/$course/exams" -Headers $hA
  "exam_count=" + $e.Count
}

TryCall 'fn3_question_mapping_available' {
  $q=Invoke-RestMethod -Method Get -Uri "$base/exams/$exam/questions" -Headers $hA
  "questions=" + $q.total
}

TryCall 'fn4_marks_input_available' {
  $m=Invoke-RestMethod -Method Get -Uri "$base/exams/$exam/marks" -Headers $hA
  "students=" + $m.total_students
}

TryCall 'fn5_co_attainment' {
  $c=Invoke-RestMethod -Method Post -Uri "$base/attainment/calculate-co?course_id=$course&exam_id=$exam&threshold_pct=0.6" -Headers $hA
  "co_rows=" + $c.attainments.Count
}

TryCall 'fn6_map_and_po_pso_attainment' {
  $m1=Invoke-RestMethod -Method Post -Uri "$base/map-co-po?course_id=$course&program_id=$program&threshold=0.25" -Headers $hA
  $m2=Invoke-RestMethod -Method Post -Uri "$base/map-co-pso?course_id=$course&program_id=$program&threshold=0.25" -Headers $hA
  $po=Invoke-RestMethod -Method Post -Uri "$base/attainment/calculate-po?course_id=$course&program_id=$program" -Headers $hA
  $pso=Invoke-RestMethod -Method Post -Uri "$base/attainment/calculate-pso?course_id=$course&program_id=$program" -Headers $hA
  "map_po=$($m1.mappings_created),map_pso=$($m2.mappings_created),po=$($po.attainments.Count),pso=$($pso.attainments.Count)"
}

TryCall 'fn7_visualization_and_reports' {
  $v=Invoke-RestMethod -Method Get -Uri "$base/visualization/$course" -Headers $hA
  $pdf=(Invoke-WebRequest -Method Get -UseBasicParsing -Uri "$base/reports/$course/download?format=pdf" -Headers $hA).StatusCode
  $xl=(Invoke-WebRequest -Method Get -UseBasicParsing -Uri "$base/reports/$course/download?format=excel" -Headers $hA).StatusCode
  "viz=$([bool]$v),pdf=$pdf,excel=$xl"
}

TryCall 'chatbot_mapping_intent' {
  $c=Invoke-RestMethod -Method Post -Uri "$base/chatbot/message" -Headers $hF -ContentType 'application/json' -Body (@{message="map co to po program_id=$program";course_id=$course}|ConvertTo-Json -Compress)
  "intent=$($c.intent),nlu=$($c.nlu_source)"
}

TryCall 'chatbot_attainment_intent' {
  $c=Invoke-RestMethod -Method Post -Uri "$base/chatbot/message" -Headers $hF -ContentType 'application/json' -Body (@{message="calculate attainment exam_id=$exam";course_id=$course}|ConvertTo-Json -Compress)
  "intent=$($c.intent),nlu=$($c.nlu_source)"
}

[pscustomobject]@{
  base=$base
  pass=($results|Where-Object status -eq 'PASS').Count
  fail=($results|Where-Object status -eq 'FAIL').Count
  results=$results
} | ConvertTo-Json -Depth 8 -Compress

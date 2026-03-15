$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:8011/api/v1'
$results = @()

function Add-Result($check, $status, $detail) {
  $script:results += [pscustomobject]@{
    check = $check
    status = $status
    detail = $detail
  }
}

function Safe-Run($name, [scriptblock]$block) {
  try {
    $r = & $block
    Add-Result $name 'PASS' ([string]$r)
  } catch {
    $msg = if ($_.ErrorDetails) { $_.ErrorDetails.Message } else { $_.Exception.Message }
    Add-Result $name 'FAIL' $msg
  }
}

$tag = [guid]::NewGuid().ToString('N').Substring(0, 8)
$adminUser = 'adm_' + $tag
$facultyUser = 'fac_' + $tag

Safe-Run 'auth_register_admin' {
  $r = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body (@{
    username = $adminUser
    email = "$adminUser@example.com"
    password = 'Pass@1234'
    full_name = 'Admin'
    role = 'admin'
  } | ConvertTo-Json -Compress) -TimeoutSec 30
  $script:adminToken = $r.access_token
  $r.role
}

Safe-Run 'auth_register_faculty' {
  $r = Invoke-RestMethod -Method Post -Uri "$base/auth/register" -ContentType 'application/json' -Body (@{
    username = $facultyUser
    email = "$facultyUser@example.com"
    password = 'Pass@1234'
    full_name = 'Faculty'
    role = 'faculty'
  } | ConvertTo-Json -Compress) -TimeoutSec 30
  $script:facultyToken = $r.access_token
  $r.role
}

if (-not $facultyToken) {
  [pscustomobject]@{ base = $base; pass = 0; fail = 1; results = $results } | ConvertTo-Json -Depth 8 -Compress
  exit 0
}

$hAdmin = @{ Authorization = "Bearer $adminToken" }
$hFaculty = @{ Authorization = "Bearer $facultyToken" }
$programId = 'PRG-' + $tag.Substring(0, 6)

Safe-Run 'seed_program_po' {
  Invoke-RestMethod -Method Post -Uri "$base/programs/$programId/outcomes" -Headers $hAdmin -ContentType 'application/json' -Body (@{ code='PO1'; statement='Apply computing fundamentals' } | ConvertTo-Json -Compress) -TimeoutSec 30 | Out-Null
  Invoke-RestMethod -Method Post -Uri "$base/programs/$programId/outcomes" -Headers $hAdmin -ContentType 'application/json' -Body (@{ code='PO2'; statement='Analyze algorithms' } | ConvertTo-Json -Compress) -TimeoutSec 30 | Out-Null
  (Invoke-RestMethod -Method Get -Uri "$base/programs/$programId/outcomes" -Headers $hFaculty -TimeoutSec 30).Count
}

Safe-Run 'seed_program_pso' {
  Invoke-RestMethod -Method Post -Uri "$base/programs/$programId/pso" -Headers $hAdmin -ContentType 'application/json' -Body (@{ code='PSO1'; statement='Build AI analytics workflows' } | ConvertTo-Json -Compress) -TimeoutSec 30 | Out-Null
  (Invoke-RestMethod -Method Get -Uri "$base/programs/$programId/pso" -Headers $hFaculty -TimeoutSec 30).Count
}

Safe-Run 'create_course' {
  $c = Invoke-RestMethod -Method Post -Uri "$base/courses" -Headers $hFaculty -ContentType 'application/json' -Body (@{
    course_code = 'CS' + (Get-Random -Minimum 1000 -Maximum 9999)
    course_name = 'OBE Verification Course'
    credits = 3
    semester = 5
    description = 'real-service verification'
    program_id = $programId
  } | ConvertTo-Json -Compress) -TimeoutSec 30
  $script:courseId = $c.id
  $c.id
}

if (-not $courseId) {
  $pass = ($results | Where-Object status -eq 'PASS').Count
  $fail = ($results | Where-Object status -eq 'FAIL').Count
  [pscustomobject]@{ base = $base; program_id = $programId; pass = $pass; fail = $fail; results = $results } | ConvertTo-Json -Depth 8 -Compress
  exit 0
}

Safe-Run 'fn1_co_generation' {
  $pos = Invoke-RestMethod -Method Get -Uri "$base/programs/$programId/outcomes" -Headers $hFaculty -TimeoutSec 30
  $psos = Invoke-RestMethod -Method Get -Uri "$base/programs/$programId/pso" -Headers $hFaculty -TimeoutSec 30
  $g = Invoke-RestMethod -Method Post -Uri "$base/courses/$courseId/generate-co" -Headers $hFaculty -ContentType 'application/json' -Body (@{
    syllabus = 'Unit1 Data structures Unit2 Algorithms Unit3 Graphs Unit4 Optimization'
    program_outcomes = $pos
    program_specific_outcomes = $psos
    num_cos = 4
  } | ConvertTo-Json -Compress -Depth 10) -TimeoutSec 120
  if ($g.course_outcomes) { $g.course_outcomes.Count } else { 0 }
}

Safe-Run 'fn2_exam_configuration' {
  $e = Invoke-RestMethod -Method Post -Uri "$base/courses/$courseId/exams" -Headers $hFaculty -ContentType 'application/json' -Body (@{
    assessment_code = 'T1'
    exam_name = 'T1 Internal'
    exam_type = 'mid_term'
    total_marks = 30
    duration_minutes = 60
    weightage_pct = 10
    units_covered = @('U1', 'U2')
    number_of_questions = 3
  } | ConvertTo-Json -Compress) -TimeoutSec 60
  $script:examId = $e.id
  $e.id
}

if ($examId) {
  Safe-Run 'fn3_question_co_mapping' {
    $coList = Invoke-RestMethod -Method Get -Uri "$base/courses/$courseId/outcomes" -Headers $hFaculty -TimeoutSec 30
    $coCode = if ($coList.Count -gt 0) { $coList[0].code } else { 'CO1' }
    $a = Invoke-RestMethod -Method Post -Uri "$base/exams/$examId/questions" -Headers $hFaculty -ContentType 'application/json' -Body (@{
      questions = @(
        @{ question_number=1; question_text='Explain merge sort complexity'; marks=10; question_type='long_answer'; co_mapped=@($coCode); override_reason='manual' },
        @{ question_number=2; question_text='Apply BFS on graph'; marks=10; question_type='long_answer'; co_mapped=@($coCode); override_reason='manual' },
        @{ question_number=3; question_text='Design stack evaluator'; marks=10; question_type='long_answer'; co_mapped=@($coCode); override_reason='manual' }
      )
    } | ConvertTo-Json -Compress -Depth 10) -TimeoutSec 90
    $a.questions_added
  }

  Safe-Run 'fn4_student_marks_input' {
    $m = Invoke-RestMethod -Method Post -Uri "$base/exams/$examId/marks" -Headers $hFaculty -ContentType 'application/json' -Body (@{
      rows = @(
        @{ student_id='S001'; marks=@{ '1'=8; '2'=7; '3'=9 } },
        @{ student_id='S002'; marks=@{ '1'=6; '2'=7; '3'=8 } },
        @{ student_id='S003'; marks=@{ '1'=9; '2'=8; '3'=10 } }
      )
    } | ConvertTo-Json -Compress -Depth 10) -TimeoutSec 60
    $m.rows_processed
  }

  Safe-Run 'fn5_co_attainment' {
    (Invoke-RestMethod -Method Post -Uri "$base/attainment/calculate-co?course_id=$courseId&exam_id=$examId&threshold_pct=0.6" -Headers $hFaculty -TimeoutSec 120).attainments.Count
  }
} else {
  Add-Result 'fn3_question_co_mapping' 'FAIL' 'Exam creation failed'
  Add-Result 'fn4_student_marks_input' 'FAIL' 'Exam creation failed'
  Add-Result 'fn5_co_attainment' 'FAIL' 'Exam creation failed'
}

Safe-Run 'fn6_po_pso_attainment' {
  $m1 = Invoke-RestMethod -Method Post -Uri "$base/map-co-po?course_id=$courseId&program_id=$programId&threshold=0.25" -Headers $hFaculty -TimeoutSec 120
  $m2 = Invoke-RestMethod -Method Post -Uri "$base/map-co-pso?course_id=$courseId&program_id=$programId&threshold=0.25" -Headers $hFaculty -TimeoutSec 120
  $po = Invoke-RestMethod -Method Post -Uri "$base/attainment/calculate-po?course_id=$courseId&program_id=$programId" -Headers $hFaculty -TimeoutSec 120
  $pso = Invoke-RestMethod -Method Post -Uri "$base/attainment/calculate-pso?course_id=$courseId&program_id=$programId" -Headers $hFaculty -TimeoutSec 120
  "map_po=$($m1.mappings_created),map_pso=$($m2.mappings_created),po_rows=$($po.attainments.Count),pso_rows=$($pso.attainments.Count)"
}

Safe-Run 'fn7_visualization_reporting' {
  $v = Invoke-RestMethod -Method Get -Uri "$base/visualization/$courseId" -Headers $hFaculty -TimeoutSec 120
  $pdf = (Invoke-WebRequest -Method Get -Uri "$base/reports/$courseId/download?format=pdf" -Headers $hFaculty -UseBasicParsing -TimeoutSec 120).StatusCode
  $excel = (Invoke-WebRequest -Method Get -Uri "$base/reports/$courseId/download?format=excel" -Headers $hFaculty -UseBasicParsing -TimeoutSec 120).StatusCode
  "viz=$([bool]$v),pdf=$pdf,excel=$excel"
}

Safe-Run 'chatbot_mapping_intent' {
  $c = Invoke-RestMethod -Method Post -Uri "$base/chatbot/message" -Headers $hFaculty -ContentType 'application/json' -Body (@{
    message = "map co to po program_id=$programId"
    course_id = $courseId
  } | ConvertTo-Json -Compress) -TimeoutSec 120
  "intent=$($c.intent),nlu=$($c.nlu_source)"
}

Safe-Run 'chatbot_attainment_intent' {
  $c = Invoke-RestMethod -Method Post -Uri "$base/chatbot/message" -Headers $hFaculty -ContentType 'application/json' -Body (@{
    message = "calculate attainment exam_id=$examId"
    course_id = $courseId
  } | ConvertTo-Json -Compress) -TimeoutSec 120
  "intent=$($c.intent),nlu=$($c.nlu_source)"
}

$pass = ($results | Where-Object status -eq 'PASS').Count
$fail = ($results | Where-Object status -eq 'FAIL').Count
[pscustomobject]@{
  base = $base
  program_id = $programId
  course_id = $courseId
  exam_id = $examId
  pass = $pass
  fail = $fail
  results = $results
} | ConvertTo-Json -Depth 10 -Compress

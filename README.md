# MMMU · L4 실행 및 별도 재채점

개인 L4 실행의 재현·결과 공유용 저장소입니다. **MMMU validation 900문항 실행과 채점은 완료됐습니다.**
이 문서는 개인 실행 기록이며 팀 제출 완료를 뜻하지 않습니다. 상세 보고서의 팀명·팀원 이름은 아직 확인되지 않았으므로, 공식 제출 전에 팀에서 채워야 합니다.

## 완료한 L4 실행

- 실행 ID `mmmu-l4-full-01`; NVIDIA L4에서 Qwen3-VL-4B-Instruct로 900/900문항 완료
- 원본 점수 **564/900 = 62.67%**. 각 30과목에 30문항씩 있어 과목별 macro average도 62.67%입니다.
- 독립 `team-final-answer-v8` 재채점은 900개 모두 검증됐고, 원본과 점수가 달라진 문항은 0개입니다.
- 813개에서 답안을 파싱했고 87개는 `NO_PARSE`였습니다. 81개가 32,768토큰 상한에 도달했습니다(정답 10, 파싱 오답 5, 미파싱 66). 총 생성량은 3,836,776토큰입니다.
- 원본·재채점 validator, 906개 Drive checkpoint ZIP의 SHA-256, 기존 713개 레코드의 재개 전후 파일 hash 검증이 통과했습니다. 900개 raw journal도 복원했습니다.
- 실행 어댑터와 Colab wrapper는 [`mmdl-colab-baseline` commit `1d895d7`](https://github.com/dust9826/mmdl-colab-baseline/commit/1d895d709c395f30ecb76bc661791ef4379e51e8), 평가 엔진은 아래 출처의 upstream commit을 사용했습니다.
- 첫 추론 시작부터 재개 실행 종료까지 **30시간 43분 19초**가 지났습니다. 이 값에는 첫 세션 중단과 복구 공백이 들어갑니다. 첫 invocation은 종료 기록이 남지 않아 순수 활성 계산 시간은 알 수 없습니다.
- 총 사용량은 **47.40 CU**(첫 세션 36.88, 재개 세션 10.52)이며, 종료 후 잔액 50.71 CU, 0 CU/시간, 활성 세션 0을 확인했습니다. CU당 결제 단가를 알 수 없어 달러 비용은 환산하지 않았습니다.

결과 문서와 작은 집계 파일을 이 저장소에 함께 보관합니다.

- [전체 실험 보고서](reports/mmmu_baseline.md)
- [전체·과목별 집계 JSON](results/l4-full-20260928/summary.json)
- [과목별 정답 수와 정확도 CSV](results/l4-full-20260928/subject_scores.csv)
- [출력 토큰 한도별 V8 절단 분석](reports/token_budget_v8.md) · [집계 JSON](results/token-budget-v8-20260930/summary.json)

추가 토큰 분석은 저장된 응답의 앞부분만 남긴 CPU 재채점입니다. 2,048토큰에서 **485/900 = 53.89%**,
8,192토큰에서 **552/900 = 61.33%**였으며, 각 한도로 모델을 새로 실행한 결과는 아닙니다.
원본 baseline은 유지하며, [재현 스크립트](scripts/analyze_token_budget.py)는 복원한 원본 artifacts와 고정 토크나이저를 필요로 합니다.

이번 결과는 한 번의 sampling 실행이며, 팀의 규칙 기반 V8 채점 결과입니다. 과제에서 인용한 67.4%와의 차이는 보고서에 비교 조건과 한계를 함께 적었습니다. 이는 공식 평가 실행의 완전한 재현 또는 모든 팀원의 최종 제출 승인을 뜻하지 않습니다.

## 출처와 역할

평가 엔진은 [jang2296/MMDL](https://github.com/jang2296/MMDL)의
`f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1` 커밋을 그대로 사용합니다.
프롬프트·V8 파서·데이터 취득·기록 형식은 해당 팀원 구현이며, 우리가 새로 만든 것으로 주장하지 않습니다.
이 저장소는 Colab 실행, Drive 백업/복원, 실행 후 별도 재채점 절차를 제공합니다.
원본 저장소는 공개 URL에서 정확한 커밋으로 clone하므로 이 비공개 저장소의 인증 정보를 Colab에 입력할 필요가 없습니다.

## 실행 상태와 확인 내역

1. **완료:** `mmmu-l4-full-01`에서 30과목×30개 입력, 전체 900개 고유 ID, 누락·미해결 실행 실패 0개를 확인했습니다.
2. **복구·보존:** 906개 checkpoint 전체를 SHA-256으로 검증해 복원했습니다. L4 실행은 완료 후 런타임 연결이 해제됐습니다.
3. **독립 채점:** 원본 응답을 유지하고 별도 `rescores/` 결과를 만들었습니다. 로컬 `validate_run`과 `validate_rescore`가 모두 통과했고, 이전 713개 기록의 파일 hash도 재개 전 값과 일치합니다.
4. **보고:** 실험 결과는 위 보고서와 집계 파일에 정리했습니다. README는 재현 안내이고 `reports/mmmu_baseline.md`가 상세 실험 기록입니다.

로컬 재검증에서 원본 rescore의 `source.json`에 Colab 절대 경로가 들어 있어 경로 비교는 임시 audit 사본에서만 정규화했습니다. 원래 rescore 산출물은 수정하지 않았습니다.

## Colab 실행

1. [colab/L4_MMMU.ipynb](colab/L4_MMMU.ipynb)를 내려받아 Colab의 파일 → 노트북 업로드로 엽니다.
2. L4 런타임을 선택하고 위에서부터 환경 준비·Drive 복원 셀을 실행합니다.
3. 기존 완료 실행의 JOB_ID는 `mmmu-l4-full-01`입니다. 독립적인 새 실행을 시작할 때는 새 JOB_ID를 지정하고, 완료된 결과를 덮어쓰지 마세요.
4. 실제 리소스 화면의 CU 잔액/시간당 요율을 확인합니다. 전체 실행 셀은 먼저 CPU로 900개 입력의 이미지 참조·장수·토큰 길이를 검사합니다. L4에 연결된 상태라면 CPU 검사 시간에도 CU가 소모될 수 있습니다.
5. 전체 실행 셀의 `RUN_FULL=True`로 설정합니다. `AUTO_DISCONNECT=True`가 기본입니다. 이 한 셀에서 입력 검사 → 추론 → 완전성 검사 → 별도 V8 재채점 → 재채점 검사 → 최종 백업 → 런타임 해제를 수행합니다.
6. 실행 셀 내부 오류도 실패 기록을 남긴 뒤 최종 백업이 성공하면 종료합니다. 백업이 실패하면 로컬 결과를 보존하려고 런타임을 유지합니다. 준비 셀의 오류나 VM 강제 종료는 이 정리 흐름 밖이므로 따로 확인하세요.

긴 실행은 한 세션에서 이어갑니다. 예기치 않은 종료 시 같은 JOB_ID로 다시 실행하면 완료 기록을 복원합니다.
**GPU·드라이버·Python·패키지·adapter가 다르면 재개가 차단됩니다.** Colab 재배정 시 이 조건이 맞는다는 보장은 없습니다.
동일 JOB_ID로 두 노트북을 동시에 실행하지 마세요. 런타임 삭제 전 최종 백업을 확인하세요.
이번 `mmmu-l4-full-01`은 이미 완료됐습니다. 재현 방법을 읽는 것만으로 기존 실행을 재개하지 마세요.

## 추론과 채점의 분리

상류 엔진은 추론하면서 기존 V8 점수도 함께 기록합니다. adapter는 파서 호출 전에 `raw_journal/<run-id>/<attempt-id>.json`에 생성 원문·토큰·입력 기록을 원자적으로 추가합니다. 채점 성공 결과와 구별해 GENERATED_UNSCORED로 표시합니다. 이 기록은 정규 문항 백업 또는 종료 시 백업에 포함되며, 강제 종료 직전 미백업 문항은 재계산될 수 있습니다.
보존된 `raw_response`를 읽는 별도 재채점 명령이 있으므로, 최종 채점은 추론과 독립적으로 반복할 수 있습니다.
추론 단계에는 GPU가 필요하지만 재채점 계산에는 GPU가 필요하지 않습니다.

**아직 완전한 추론 전용 모드는 아닙니다.** 파서 예외는 실행을 멈춥니다. 새 journal 덕분에 생성 원문은 남지만, 상류 재채점 명령은 COMPLETE인 900개 samples만 받습니다. 예외가 생긴 journal의 CPU 복구/새 파서 연결은 별도 작업이며, 단순 재개는 그 실패 문항을 다시 생성합니다. 이를 완료 성적으로 합치거나 파서 오류를 일반 오답으로 숨기지 않습니다.

환경 설치 및 데이터 준비 후 원본 엔진의 한 명령 실행:

```bash
bash scripts/eval.sh --protocol configs/eval/mmmu_val_v8.yaml \
  --hardware "$HARDWARE_CONFIG" --model-ref manifests/models/baseline.json \
  --model-path Qwen/Qwen3-VL-4B-Instruct --data-root "$DATA_ROOT/evaluation/mmmu" \
  --artifact-root "$ARTIFACT_ROOT" --public-root "$ARTIFACT_ROOT/public" \
  --job-id "$JOB_ID" --run-role evaluation \
  --require-commit f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1 \
  --run-id "${JOB_ID}-evaluation" --mode full
```

위 명령은 원본 엔진의 깨끗한 checkout에서 실행합니다. Colab에서는 노트북이 hardware 파일·경로·설치를 준비하고
동일 CLI에 백업 adapter를 연결합니다. 직접 명령은 Drive 백업을 제공하지 않습니다.

보존된 결과의 별도 재채점도 원본 엔진 checkout에서 실행합니다:

```bash
bash scripts/rescore.sh --artifact-root "$ARTIFACT_ROOT" \
  --run-id "${JOB_ID}-evaluation" --parser team-final-answer-v8 \
  --output-dir "$ARTIFACT_ROOT/rescores/${JOB_ID}-v8-review-01"
python -m scripts.validate_rescore \
  --source-run "$ARTIFACT_ROOT/runs/${JOB_ID}-evaluation" \
  --scored-dir "$ARTIFACT_ROOT/rescores/${JOB_ID}-v8-review-01"
```

출력 폴더는 매번 새로 지정합니다. 이 검증기는 V8 전용이며 새로운 파서는 그 규칙에 맞는 검증이 필요합니다.
새 파서가 필요하면 구현·테스트·선택 근거를 추가하고 모든 문항에 동일 적용합니다. 정답별 예외 규칙을 만들지 않습니다.
프롬프트/모델/이미지 해상도/생성 설정 변경은 새 추론 실행이며 재채점만으로 대체할 수 없습니다.

## 보존 대상과 설정

- 고정 모델: Qwen/Qwen3-VL-4B-Instruct @ `ebb281ec70b05090aa6165b016eac8ec08e71b17`, BF16 비양자화
- 고정 데이터: MMMU/MMMU @ `98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68`, validation 900문항
- 프로토콜: 상류 `configs/eval/mmmu_val_v8.yaml`; 파라미터 전문과 프롬프트는 그 커밋에서 확인
- 문항 ID, 원문 응답, 추출 답, 정답 여부, 종료 사유, 시간, 토큰 수, 환경/설정/소스 hash를 원본 run에 보존
- Drive: `MyDrive/MMDL-Colab/<JOB_ID>/`에 증분 ZIP과 SHA-256 완료 marker
- ZIP과 marker는 전체 시퀀스를 함께 보존해야 복원 가능. 마지막 ZIP 하나만 보관하지 말 것
- 모델 가중치·이미지·원문 데이터·응답·인증 정보는 Git에 커밋하지 않음

## 과거 사전 실행과 현재 완료 상태

2026-09-26의 A100/L4 회계 3문항 테스트는 사전 smoke test이며, 두 기기 모두 3/3 정답을 냈습니다. 평가 구간은 각각 39.37초/45.65초였습니다. 이는 전체 900문항 결과와 별개이고 전체 정확도 추정치가 아닙니다.

그 뒤 전체 입력 검사·journal·Drive 증분 백업과 복구, 재채점, 검증 및 런타임 종료를 실제 L4에서 완료했습니다. 한 차례 세션 중단은 713개 결과를 보존·복원한 뒤 같은 환경에서 이어갔습니다. 총 완료 시간 30시간 43분 19초에는 중단·복구 간격이 포함되므로 순수 추론 시간을 뜻하지 않습니다. 관측 CU 사용량은 준비·설정과 두 세션을 합친 값이며 달러 비용은 계정 CU 가격을 알 수 없어 계산하지 않았습니다.

[과제 안내](https://gist.github.com/neur-lab/38deabdfcde9e6dbacf362ab8059eb41) ·
[제출 템플릿](https://gist.github.com/neur-lab/483852e1f9d8d52f54627e600677c2f9)

## 2026-09-26 실행 전 검토 기록

- 정상: 모델/데이터 revision, 30×30 coverage, gold 분리, 다중 이미지 순서, 단일 resize, 원문/토큰/환경 보존, 원본을 바꾸지 않는 별도 재채점.
- 수정: 파서 예외 전에 생성 원문 journal 보존. 전체 실행/검증/백업/종료를 같은 try/finally에 연결. 중단된 재채점 폴더를 덮어쓰지 않도록 실행마다 새 경로 사용.
- 추가: 실제 processor로 900개 입력을 사전 검사하는 단계. 이미지 5개 및 입력+출력40960 상한을 초과하면 GPU 모델 로딩 전에 중단.
- V8 한계: `Final answer: B. This answer is correct.`가 NO_PARSE로 처리되는 사례 확인. 5,000자리 분수는 예외 발생. 복합 단위·동의어는 보수적 처리. 수정된 파서는 별도 버전과 근거가 필요하며 기본 V8은 변경하지 않음.
- 상류 파서/저장/재채점 CPU 검사 46개 통과. 이 저장소의 회귀 검사 7개 통과(실제 CUDA 대신 합성 객체 사용).
- 당시 남은 확인은 후속 900문항 실행에서 닫혔습니다. 전체 run·재채점 validator가 통과했고 checkpoint 및 기존 복구 파일 hash도 검증했습니다. 단, 첫 invocation 종료 시각과 순수 활성 GPU 계산 시간은 기록되지 않았습니다.
- adapter hash가 변경되었으므로 이전 3문항 smoke 실행에 새 adapter로 이어 붙이지 않음. 새 전체 JOB_ID 사용.

실행 전 기록에 적힌 파서 예외·`NO_PARSE` 사례는 설계 한계 관찰입니다. V8 파서를 수정하거나 이 문제를 해결했다고 주장하지 않습니다. 전체 실행에서는 `NO_PARSE` 87개를 별도로 집계했으며, 각 오답의 원인은 문항별 검토 없이 단정하지 않습니다.

```bash
python3 -m unittest discover -s tests -v
```

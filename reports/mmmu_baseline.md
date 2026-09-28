# MMMU-val Baseline Evaluation Report — Qwen3-VL-4B-Instruct

- **팀명**: 제출 전 기입
- **팀원**: 제출 전 기입
- **작성일**: 2026-09-28
- **문서 범위**: 개인 Colab L4 실행 결과 공유. 팀 최종 제출·승인 여부와 구분한다.
- **재현 커맨드**: 환경·데이터 준비 후 §1의 `python colab_runner.py ... --mode full` 실행

**900문항 평가와 독립 V8 재채점을 완료했다. 최종 정답은 564개, 종합 정확도는 62.67%다.**
원본/재채점 검증, Drive 전체 백업 복원, 런타임 해제까지 확인했다.
[기계 판독용 결과·검증 요약](../results/l4-full-20260928/summary.json)과
[과목별 점수·시간 CSV](../results/l4-full-20260928/subject_scores.csv)를 함께 제공한다.

이 보고서는 [공식 제출 템플릿](https://gist.github.com/neur-lab/483852e1f9d8d52f54627e600677c2f9)의 8개 항목을 따른다.
평가 엔진·프롬프트·V8 파서는 팀원의 [jang2296/MMDL](https://github.com/jang2296/MMDL/tree/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1)을 차용했다.
이 저장소에서 추가한 범위는 Colab 실행, 입력 사전 검사, 채점 전 원문 보존, Drive 백업·복원 및 종료 절차다.

## 1. 환경 / 재현성

| 항목 | 값 |
|---|---|
| 모델 checkpoint | `Qwen/Qwen3-VL-4B-Instruct` @ `ebb281ec70b05090aa6165b016eac8ec08e71b17` |
| 정밀도 | BF16, 비양자화. Processor·Tokenizer도 같은 revision |
| 데이터 | `MMMU/MMMU` @ `98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68`; validation 30과목 × 30문항 |
| GPU | Google Colab NVIDIA L4 1장; `nvidia-smi` 총 메모리 23,034MiB |
| 추론 백엔드 | vLLM 0.11.0; 연속 처리, 동시 요청 최대 2개, eager 실행; GPU에 전체 모델 배치 |
| 주요 환경 | Linux, Python 3.12.3, PyTorch 2.8.0+cu128, Transformers 4.57.1, qwen-vl-utils 0.0.14 |
| 의존성 | [고정 requirements-vllm.lock](https://github.com/jang2296/MMDL/blob/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1/env/requirements-vllm.lock); 설치 흐름은 [Colab 노트북](../colab/L4_MMMU.ipynb) |
| 실행 당시 wrapper commit | `1d895d709c395f30ecb76bc661791ef4379e51e8` |
| 상류 엔진 commit | `f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1` |
| adapter SHA-256 | `0fb82da1c733b0e8d61391561d4568492150ae55a9b84e14f74376c15de3b966` |
| 실행 식별자 | JOB_ID `mmmu-l4-full-01`; run_id `mmmu-l4-full-01-evaluation` |
| 실측 peak VRAM | summary의 **장치 전체 사용량 관측 최대 21.38GiB** (22,951,231,488 bytes). vLLM allocator peak는 미측정이며 모델 가중치 크기와 같지 않음 |
| 900문항 전체 경과 | **30시간 43분 19초**. 첫 추론 시작부터 마지막 추론 종료까지이며 중단·복구 포함 |
| 재개 호출의 평가 루프 | 23,407.670초. 복구 후 남은 187문항 구간이며 900문항 전체 시간이 아님 |
| 계산 단위(CU) | **47.40 CU** 사용: 시작 98.11 → 종료 후 50.71. 준비와 두 세션 포함; 달러 단가 미확인 |

vLLM을 사용한 이유는 응답 길이가 다른 문항을 최대 2개씩 처리하면서, 먼저 끝난 요청 자리에 다음 문항을 투입하기 위해서다.
L4에서는 기존 3문항 smoke 테스트와 BF16 검사를 거쳐 전체 실행에 진입했다. 작은 테스트의 속도는 전체 완료 시간의 보장이 아니었다.

### 실행 방법

[README의 준비 절차](../README.md#colab-실행)에 따라 노트북을 업로드하고 L4 및 Drive를 연결한다.
노트북은 고정 상류 commit을 취득하고 Python 3.12.3·의존성·모델·데이터·hardware 파일을 준비한다.
전체 셀은 입력 검사 → 추론·기본 채점 → 원본 검증 → 별도 V8 재채점·검증 → 최종 백업 → 런타임 해제를 수행한다.
저장소 노트북의 `RUN_FULL` 기본값은 `False`이며 실행할 때만 `True`로 바꾼다.
**새 재현 실행은 새 JOB_ID를 사용하고, 완료된 `mmmu-l4-full-01`에 다른 조건을 이어 붙이지 않는다.**

동일 adapter를 통한 추론·채점은 준비된 환경에서 아래 한 커맨드로 실행할 수 있다.
아래 경로는 Colab 준비 셀의 기본 경로 예시이며, 다른 환경에서는 해당 환경변수만 바꾼다.
`MMDL_MODEL_PATH`에는 공식 ID 또는 지정 revision을 받은 로컬 snapshot 경로를 넣는다.

```bash
export MMDL_JOB_ID=mmmu-l4-reproduce-01
export MMDL_ENGINE_ROOT=/content/MMDL
export MMDL_RUNNER=/content/colab_runner.py
export MMDL_PYTHON=/content/mmdl-env/bin/python
export MMDL_HARDWARE_CONFIG=/content/colab-hardware.json
export MMDL_DATA_ROOT=/content/mmdl-data
export MMDL_MODEL_PATH=Qwen/Qwen3-VL-4B-Instruct
export MMDL_ARTIFACT_ROOT="/content/mmdl-artifacts-${MMDL_JOB_ID}"
export MMDL_COLAB_BACKUP="/content/drive/MyDrive/MMDL-Colab/${MMDL_JOB_ID}"
export HF_HOME=/content/mmdl-cache/huggingface
export CUDA_VISIBLE_DEVICES=0
export TOKENIZERS_PARALLELISM=false
export VLLM_WORKER_MULTIPROC_METHOD=spawn
cd "$MMDL_ENGINE_ROOT"
```

```bash
"$MMDL_PYTHON" "$MMDL_RUNNER" \
  --protocol "$MMDL_ENGINE_ROOT/configs/eval/mmmu_val_v8.yaml" \
  --hardware "$MMDL_HARDWARE_CONFIG" \
  --model-ref "$MMDL_ENGINE_ROOT/manifests/models/baseline.json" \
  --model-path "$MMDL_MODEL_PATH" \
  --data-root "$MMDL_DATA_ROOT/evaluation/mmmu" \
  --artifact-root "$MMDL_ARTIFACT_ROOT" \
  --public-root "$MMDL_ARTIFACT_ROOT/public" \
  --require-commit f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1 \
  --job-id "$MMDL_JOB_ID" --run-role evaluation \
  --run-id "${MMDL_JOB_ID}-evaluation" --mode full --no-download
```

`--no-download`는 준비 단계에서 모델·데이터 취득을 마쳤다는 전제다. 위 직접 명령은 추론·기본 채점·원문 보존·증분 백업을 실행한다.
입력 사전 검사, 별도 재채점과 자동 런타임 해제를 포함한 전체 운영 흐름은 노트북의 마지막 실행 셀을 사용한다.
순수 CPU 재채점 명령은 [README의 채점 분리 절차](../README.md#추론과-채점의-분리)에 있다.
GPU·환경·스케줄링에 따른 수치적 차이 때문에 같은 seed라도 개별 응답의 완전한 일치를 보장하지 않는다.

## 2. 프롬프트

실제 적용한 P0 텍스트 템플릿은 아래와 같다. 이 텍스트에 지정 모델의 chat template을 적용한다.

객관식:

```text
{hint_prefix}Question: {question}
Options:
{options}Please select the correct answer from the options above.
```

주관식:

```text
{hint_prefix}Question: {question}
```

- `{question}`는 원본 질문이다. hint가 있으면 `{hint_prefix}`에 `Hint: {hint}`와 줄바꿈을 넣고, 없으면 빈 문자열을 쓴다.
- `{options}`는 실제 보기 수와 순서를 유지해 `A. ...`, `B. ...` 등을 줄마다 배치한다. A–D로 고정하지 않는다.
- 이미지 참조 순서대로 이미지를 먼저 넣고 텍스트를 마지막에 붙인다. `apply_chat_template(add_generation_prompt=True)`를 적용한다.
- 정답·해설은 모델 입력에서 제외한다. 추가 system, few-shot, 단계별 풀이 지시는 넣지 않는다.

**출처:** [Qwen 공개 MMMU prompt 구성 코드](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/run_mmmu.py),
상류의 [객관식 템플릿](https://github.com/jang2296/MMDL/blob/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1/prompts/mmmu_mcq_v1.txt)·[주관식 템플릿](https://github.com/jang2296/MMDL/blob/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1/prompts/mmmu_open_v1.txt).
**선택 이유:** 팀원이 구현한 공개 평가 프롬프트를 그대로 유지해 입력 조건을 고정하고, 임의의 추가 지시가 점수에 미치는 영향을 줄이고자 했다.
공식 평가 전체를 동일하게 복제했다는 의미는 아니다.

## 3. 생성(Decoding) 설정

### 3.1 Sampling recipe

| 파라미터 | 값 |
|---|---|
| `do_sample` | `true` |
| `temperature` | `0.7` |
| `top_p` | `0.8` |
| `top_k` | `20` |
| `repetition_penalty` | `1.0` |
| `presence_penalty` | `1.5` |
| 기준 `seed` | `3407` |
| 문항별 seed | `int.from_bytes(SHA256("3407:{sample_id}")[:8], "big") mod 2^31` |

**출처:** [Qwen 공식 README의 Evaluation Reproduction / Instruct models](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/README.md#evaluation-reproduction).
공식 안내의 sampling 값을 사용했으며 속도 때문에 greedy로 바꾸지 않았다.
문항별 SHA-256 seed 계산은 재개 전후 문항별 난수를 유지하려는 **차용한 팀 자체 정책**이다.
공식 공개 MMMU 스크립트는 엔진 seed 42를 사용하므로, 공식 실행과 난수 흐름까지 같다고 보지 않는다.

### 3.2 생성 예산 / 이미지 해상도

| 파라미터 | 값 |
|---|---|
| `max_new_tokens` | `32768` |
| `min_pixels` / `max_pixels` | `1003520` / `4014080` |
| 이미지 처리 | qwen-vl-utils 0.0.14에서 비율을 유지해 resize, 이후 지정 Processor 적용 |
| 문맥 한도 | `40960` tokens |
| 동시 처리 | 최대 2개 요청, continuous scheduling, eager |
| 실입력 검사 | 900/900 PASS; 최대 입력 5,627토큰, 최대 이미지 5장 |

**선택 근거:** 출력 32,768은 Qwen 공식 평가 recipe와 팀원 조건을 유지하기 위한 상한이다.
긴 풀이를 수용하는 대신 반복 생성이 길어지면 시간과 CU 부담이 커진다. 실제 81문항이 상한에 도달했다.
이미지 픽셀 범위는 [공개 MMMU 코드](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/run_mmmu.py)의
`1280×28×28`–`5120×28×28`을 따른다. 이미지마다 적용되는 픽셀 예산이며 고정 가로·세로 크기가 아니다.
세부 정보 보존과 메모리·속도 사이의 선택으로, 확대가 정확도 향상을 보장하지 않는다.
입력 최대 5,627과 출력 상한을 더한 38,395가 문맥 40,960 이내임을 실행 전에 확인했다.
실행 도중 해상도·출력 길이·정밀도를 변경하지 않았다.

## 4. 채점(파싱) 방식

**사용한 로직:** 상류의 [team-final-answer-v8](https://github.com/jang2296/MMDL/blob/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1/src/mmdl/evaluation/final_answer_parser_v8.py)를 그대로 사용했다.
파서 자체를 이 Colab 실행에서 새로 개발하거나 튜닝한 것은 아니다.
MMMU 공식 숫자 정규화 함수는 상류의 [third_party 출처](https://github.com/jang2296/MMDL/blob/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1/third_party/README.md)에 고정돼 있다.

1. 원본 응답을 별도 보존한 뒤 추출용 텍스트의 Markdown·공백·지원 수식 표기를 정규화한다.
2. 명시적인 최종답 선언과 수정·철회·충돌을 확인한다. 선언이 없을 때에만 말미 답안·boxed·보기 내용 등 지원 규칙을 적용한다.
3. 객관식은 실제 보기 중 하나를 추출해 비교한다. 여러 후보가 남으면 정답을 임의 선택하지 않는다.
4. 주관식은 단일 수치 또는 정규화한 전체 문자열을 비교한다. 숫자에는 공식 함수의 소수점 두 자리 반올림 규칙을 사용한다. 범용 단위 환산·의미상 동의어 추론은 하지 않는다.
5. `NO_PARSE`와 빈 답은 오답으로 계산하되 별도 표시한다. 출력 상한 종료도 완성된 답이 추출되고 충돌이 없다면 정답일 수 있다.

정답 추출에는 기준 정답을 사용하지 않으며 LLM 판정·재생성·무작위 선택·이전 파서 fallback은 없다. 분모는 항상 900이다.
추론 중 원본 V8 점수를 기록하고, 보존된 응답을 읽어 별도 폴더에서 V8 CPU 재채점을 수행했다.
**900문항 모두 채점 결과가 일치했다.** 이는 구현·보존 결과의 일관성 검증이며 파서의 모든 판단이 사람 판단과 같다는 증명은 아니다.
향후 다른 채점 규칙을 비교할 때도 생성 원문을 유지하고 별도 결과로 기록한다.

## 5. 결과

| No. | Subject | Data Num | Correct | Acc |
|---:|---|---:|---:|---:|
| 1 | Accounting | 30 | 20 | 66.67% |
| 2 | Agriculture | 30 | 14 | 46.67% |
| 3 | Architecture_and_Engineering | 30 | 14 | 46.67% |
| 4 | Art | 30 | 19 | 63.33% |
| 5 | Art_Theory | 30 | 26 | 86.67% |
| 6 | Basic_Medical_Science | 30 | 22 | 73.33% |
| 7 | Biology | 30 | 16 | 53.33% |
| 8 | Chemistry | 30 | 11 | 36.67% |
| 9 | Clinical_Medicine | 30 | 22 | 73.33% |
| 10 | Computer_Science | 30 | 19 | 63.33% |
| 11 | Design | 30 | 23 | 76.67% |
| 12 | Diagnostics_and_Laboratory_Medicine | 30 | 10 | 33.33% |
| 13 | Economics | 30 | 25 | 83.33% |
| 14 | Electronics | 30 | 12 | 40.00% |
| 15 | Energy_and_Power | 30 | 14 | 46.67% |
| 16 | Finance | 30 | 21 | 70.00% |
| 17 | Geography | 30 | 14 | 46.67% |
| 18 | History | 30 | 21 | 70.00% |
| 19 | Literature | 30 | 24 | 80.00% |
| 20 | Manage | 30 | 22 | 73.33% |
| 21 | Marketing | 30 | 24 | 80.00% |
| 22 | Materials | 30 | 14 | 46.67% |
| 23 | Math | 30 | 18 | 60.00% |
| 24 | Mechanical_Engineering | 30 | 15 | 50.00% |
| 25 | Music | 30 | 7 | 23.33% |
| 26 | Pharmacy | 30 | 22 | 73.33% |
| 27 | Physics | 30 | 25 | 83.33% |
| 28 | Psychology | 30 | 24 | 80.00% |
| 29 | Public_Health | 30 | 27 | 90.00% |
| 30 | Sociology | 30 | 19 | 63.33% |
| | **Overall (macro avg)** | **900** | **564** | **62.67%** |

계산식: `Overall = mean(30개 과목의 반올림 전 accuracy) = 564/900 × 100 = 62.666666…%`.
모든 과목이 30문항이므로 macro average와 전체 정답 비율이 같다.
누락·외부 실행 오류·미해결 실행 오류는 0건이다. 파싱 실패와 내용상 오답은 아래와 같이 분모에 포함했다.

| 종료 사유 | 문항 | 파싱·정답 | 파싱·오답 | NO_PARSE | 생성 토큰 |
|---|---:|---:|---:|---:|---:|
| `stop` | 819 | 554 | 244 | 21 | 1,182,568 |
| `length` | 81 | 10 | 5 | 66 | 2,654,208 |
| 합계 | 900 | 564 | 249 | 87 | 3,836,776 |

문항당 출력 중앙값은 464토큰, 평균은 약 4,263토큰이다. **상한 종료 81개(9.0%)가 전체 출력 토큰의 69.18%를 차지했다.**
토큰 비중이 곧 실행 시간 비중은 아니지만, 짧은 smoke 테스트보다 전체 실행이 오래 걸린 양상을 뒷받침한다.
CSV의 `generation_seconds`는 동시 요청에 배분한 엔진 시간이며 `sample_seconds`는 겹치는 요청 지연 시간이다. 이를 전체 실행 wall time으로 합산하지 않는다.

## 6. 공식 수치와의 비교

| 구분 | Overall (MMMU val) |
|---|---:|
| 과제에서 제시한 공식 비교값 | 67.40% |
| 이번 L4 실행·V8 평가 | 62.67% |
| 차이: 이번 실행 − 공식 | **−4.73%p** |

비교값의 출처는 [과제 안내](https://gist.github.com/neur-lab/38deabdfcde9e6dbacf362ab8059eb41)다.
차이는 반올림 전 측정값으로 계산했다. 팀원의 별도 RTX3090 실행 62.00%보다 0.67%p 높지만,
서로 다른 한 번의 sampling 결과이므로 이를 L4의 정확도 우위로 해석하지 않는다.
[팀원 기준 보고서](https://github.com/jang2296/MMDL/blob/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1/reports/mmmu_baseline.md)

## 7. 격차 분석

규칙 기반 V8은 최종답을 명확히 추출하지 못하면 오답 처리한다. Qwen 공개 평가 설명은 모호한 답에 모델 기반 추출도 사용하는 반면, 이번 실행은 이를 사용하지 않았다([공개 채점 설명](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/mmmu/README.md#custom-evaluation-logic)). 따라서 표현·충돌 처리 차이가 점수에 영향을 줄 수 있다. NO_PARSE 87개와 상한 종료 81개는 66개가 겹치므로 별도 손실로 합산할 수 없다. Accounting 15·17은 32,768토큰 동안 계산을 반복 검토하다 최종답을 추출하지 못했다. 반면 Accounting 19는 670토큰으로 정상 종료하고 B를 추출했지만 정답 C와 달랐다. 출력 형식 문제와 내용상 오답이 함께 존재한다. 문항별 seed 정책·백엔드·장비도 공식 실행과 완전히 같지 않다. 공식 문항별 원문 및 채점 대조 실험이 없어 각 원인의 기여도는 확정할 수 없다. 추출 실패 87개를 전부 모델 오류나 전부 파서 오류로 간주하지 않는다.

## 8. 기타 특이사항 / 한계

### 연결 중단과 동일 조건 복구

- 첫 추론 시작: 9월 27일 00:23:58 KST. 첫 세션은 약 24시간 뒤 연결이 끊겼고 정확한 종료 원인은 확인하지 못했다.
- 713개 결과를 checkpoint 715까지의 백업에서 복원했다. GPU·드라이버·Python·전체 패키지·adapter 식별값과 BF16을 확인한 뒤 9월 28일 00:37:13 KST에 재개했다.
- 남은 187개를 완료한 시각은 9월 28일 07:07:17 KST다. 첫 invocation은 종료 시각 없이 `RUNNING` 상태로 남아 있어, 순수 계산 시간과 정확한 복구 공백은 확정할 수 없다.
- 원본 검증과 별도 V8 재채점 검증 후 checkpoint 906까지 최종 백업됐고, 런타임은 해제됐다. 자원 화면에서 0 CU/시간·활성 세션 0을 확인했다.
- 47.40 CU는 첫 세션 36.88 + 둘째 세션 10.52의 합이다. 잔액의 소수점 둘째 자리 표시 차이이며 모델 로딩·준비 등을 포함한다. CU당 결제 단가를 확인하지 않아 달러 비용으로 환산하지 않았다.

### 검증과 결과 보존

| 확인 항목 | 결과 |
|---|---|
| 실제 입력 사전 검사 | 900개 고유 ID PASS, 최대 입력 5,627토큰·이미지 5장 |
| 원본 결과 검증 | 900개 ID·30과목·정답 합계·레코드/입력 hash·시간·viewer 이미지·원문 재채점 PASS |
| 독립 V8 재채점 | 900개 검증 PASS, 채점 결과 변경 0개, 추론 관련 필드 보존 |
| Drive → 로컬 복원 | 순서가 연속인 906개 checkpoint ZIP 및 완료 marker 전체 확보, 각 ZIP SHA-256 PASS |
| 중단 전 결과 보존 | 기존 713개 파일 SHA-256이 최종 복원본에서도 모두 일치 |
| 채점 전 journal | 900개 확보 |
| 종료 | 최종 백업 성공, 런타임 해제 확인 |

로컬 V8 검증은 Colab의 절대 경로가 기록된 `source.json` 때문에 그대로는 경로 검사를 통과하지 못했다.
**임시 검사용 사본의 `source_run` 위치만 로컬 경로로 바꾸어** 원래 검증기를 실행했고 모든 검사를 통과했다.
보존된 원본 파일·파서·점수는 변경하지 않았다. 검증 요약과 해시는 [summary.json](../results/l4-full-20260928/summary.json)에 있다.

전체 원장은 Drive `MyDrive/MMDL-Colab/mmmu-l4-full-01/`와 별도 로컬 보관본에 있다.
**마지막 ZIP 하나로는 복원할 수 없으며 1–906의 ZIP과 완료 marker 전체가 필요하다.**
Git에는 이 보고서·작은 집계·실행 코드를 포함하고, 모델 가중치·데이터 이미지·대용량 원문 응답·HTML 열람본은 별도 보존한다.
따라서 저장소만으로 기존 900개 응답을 그대로 재채점할 수는 없고, 보존 원장을 함께 받아야 한다. 새 추론은 위 고정 조건으로 재현할 수 있다.

이번 실행은 fine-tuning 결과가 아닌 단일 baseline이다. 과목별 30문항의 차이로 능력 전반을 단정하지 않는다.
출력 길이 단축, 다른 GPU의 전체 실행, 새 파서와 기존 파서의 통제 비교는 추가 실험으로 남아 있다.
평가와 검증은 완료했지만 **팀명·명단 기입, 팀 검토 및 과제 제출은 별도 단계**다.

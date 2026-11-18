# 마무리 SFT · 첫 gradient 원인 진단과 결정적 학습

**검증 완료: 실제 FlashAttention 역전파의 비결정성을 재현했고, 고정한 새 실행 조건에서 두 독립 LoRA 학습의 가중치·24문항 응답이 모두 일치했다.**

## 목적

[앞선 재현 검사](../finish_sft_20261118/README.md)에서는 같은 초기 LoRA·자료·순서·시드에도 첫 gradient와 최종 가중치가 달랐다. 같은 가중치의 고정24문항 추론은 반복 일치했다. 이번에는 **실제 연산에서 gradient 차이를 재현하고, 결정적 실행 조건으로 학습 자체의 반복 일치를 검사**한다.

학습 목표나 정답 데이터를 바꾸는 성능 개선 실험은 아니다. 과거493/900 어댑터는 회수하지 못했으며, 이번 조건으로 그 점수를 재현한다고 주장하지 않는다.

## 변경하지 않는 부분

- 원본 `Qwen/Qwen3-VL-4B-Instruct`, revision `ebb281ec70b05090aa6165b016eac8ec08e71b17`.
- 원래 자체 합성48개 이미지·초안 token IDs·검산한 마무리 token IDs·EOS. 자료 SHA256 `1ca52b224f3c03dfae2d3297d9bfc8a0e563936afc117293e9d5f2e65cc09070`.
- 긴 초안은 context, 마무리+EOS에만 CE loss. 언어모델36개 층 Q/V LoRA(r8/alpha16/dropout0), AdamW5e-5/weight decay0, 누적4·clip1,2epoch/24업데이트, 실제 감독 token IDs7,610개.
- 학습 시드3407, epoch별 순서3407/3408. A와 B는 각각 원본 Qwen에서 독립적으로 새 LoRA를 학습한다.
- 원래 학습 함수와 평가 구현을 포함한 [기존 실행 코어](../finish_sft_20261118/reproduce.py)를 그대로 호출한다. 코어 SHA256은 `49e2126670434e0ca1960d758a2d08c8bd2664f59f57423fe55f9dcaccf5fffe`다.
- 기존 [고정 자료 묶음](../finish_sft_20261118/frozen_bundle.zip)의 SHA256은 `0bc1895db561eca1440e820bdbfb067d256ad7a847342e22c4e96f6ded56fb98`다. 공개 묶음에 공식 MMMU 질문·보기·정답·원본 이미지를 넣지 않았다.
- Python3.12.3 / torch2.8.0+cu128 / transformers4.57.1 / peft0.17.1 / vLLM0.11.0 / L4.

## 실제 원인 확인 방법

1. 기존 SDPA 설정으로 원래 첫4문항을 역전파하되 첫 optimizer.step 전에 멈춘다. 이 진단은 optimizer 업데이트0회다.
2. CPU profiler에서 실제 호출된 attention 연산 이름을 기록한다. 첫 decoder attention의 실제 Q/K/V와 들어오는 gradient를 보존한다.
3. 그 입력과 gradient를 고정하고 SDPA를 조건별3회 재실행한다. 첫 두 조건에서는 **deterministic_algorithms flag만** 바꾼다. 입력·출력·Q/K/V gradient의 해시와 최대 절대 차이, 연산 이름을 남긴다.
4. 수학 SDPA도 참조 조건으로 검사한다. 다른 backend 사이의 출력값이 같아야 한다고 요구하지 않는다. 각 고정 조건 안에서의 반복 일치를 검사한다.

| 연산 재실행 조건 | 통제 |
|---|---|
| default_repeat | 기존 자동 SDPA, deterministic=False |
| deterministic_flag | 같은 자동 SDPA, deterministic=True/warn_only=False |
| math_reference | deterministic=True/warn_only=False, math SDPA만 허용 |

진단 프로세스의 cuBLAS workspace는 모든 조건에서 동일하게 고정한다. 이 국소 실험은 과거 전체 프로세스의 모든 계산을 복제하는 것이 아니라, 실제 layer 입력으로 해당 연산의 반복성을 조사하는 것이다. scalar loss만 같다는 이유로 전체 forward가 같다고 가정하지 않는다.

## 학습 실행 조건과 사전 검사

- 프로세스 시작 전 `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `PYTHONHASHSEED=3407`, `OMP_NUM_THREADS=6`, `MKL_NUM_THREADS=6`.
- Python/NumPy/PyTorch/CUDA seed3407, CPU threads6/inter-op1.
- `torch.use_deterministic_algorithms(True, warn_only=False)`. 지원하지 않는 비결정적 연산을 경고만 내고 계속 실행하지 않는다.
- cuDNN deterministic=True/benchmark=False, TF32 및 저정밀 reduction 비활성화.
- 우선 자동 SDPA의 결정적 경로를 사용한다. 이 조건의 전체 첫4문항 gradient를 두 새 프로세스에서 검사한다.
- 초기값·입력·전체 첫 logits·logp·첫 gradient가 두 프로세스에서 일치해야 전체 학습으로 넘어간다. 자동 SDPA 조건이 실패하면 math SDPA 조건으로 같은 사전 검사를 한 번만 대체하고, 변경 이유를 기록한다. 둘 다 실패하면 전체 학습을 시작하지 않는다.

이 설정은 원래 경로의 단순 재실행과 구별하는 **새 수치 실행 조건**이다. 다른 하드웨어·드라이버·PyTorch 버전의 동일 결과까지 보장하지 않는다.

## 전체 학습 및 평가 검증

선택된 한 조건으로48개 전체 학습을 새 프로세스에서 두 번 수행한다. 각 실제 어댑터를 먼저 백업하고 다시 회수해 검증한 뒤 다음 단계로 넘어간다.

- 초기 LoRA144개와 입력48개 해시,96개 forward logp 기록, 첫4개의 전체 마무리 logits 해시.
- 24업데이트의 clipping 전 gradient 전체 해시·loss·gradient norm.
- 실제 adapter 재로딩,144개 최종 텐서 값,파일 SHA256, merged 가중치 파일 해시.
- 기존 첫 Accounting24개 요청 묶음의 A/B 응답: P0·2048·V8·engine3407·문항별seed·MP0·max_num_seqs8/요청24/context12288. 각각 새 vLLM 프로세스에서 평가한다.
- 24고유ID·입력/실제 prompt token IDs 해시·seed 일치, 원문·토큰열·종료 사유, 저장 응답48개의 별도V8 재채점.

MMMU900은 학습에 사용하지 않는다. 첫24개는 재현성 진단 표본이며 전체 정확도 추정이나 공학 분야 효과를 판단할 표본이 아니다. vLLM0.11.0은 BATCH_INVARIANT 미지원이며 이번에도 배치 불변성을 주장하지 않는다.

## 실행·백업

`Finish_SFT_deterministic_L4.ipynb`는 고정 소스·자료를 내장한다. Colab Drive 인증이나 수동 학습자료 업로드 없이 실행한다. 모델/평가 자료는 공식 고정 revision에서 받는다.

실제 L4 계산 상한3시간, 백업 확인 대기10분, 완료/실패 시 runtime.unassign을 설정했다. 종료 후 활성 세션0을 별도로 확인한다. 기존 탭을 닫거나 실행 중 셀을 재실행하지 않고, keep-alive나 예약 작업을 만들지 않는다.

백업 순서는 `diagnosis → train_A → train_B → compare → final`의5개 증분 ZIP과ready marker다. **마지막ZIP만으로는 복구되지 않는다.** [복구 도구](../finish_sft_20261118/recover_checkpoint.py)는 각 출력 텍스트에서 완성된 packet을 복구하고 SHA256·CRC·전체 파일 목록·각 파일 해시·경로/크기 제한을 검사한다. ZIP을 본인 Drive에 업로드하고 실제로 다시 받은 바이트를 검증한 뒤 실제 파일ID:SHA256을 입력한다. 입력 문자열만으로 Drive 검증이 자동 실행되는 것은 아니다.

## 원문 근거

- [PyTorch2.8 재현성 문서](https://docs.pytorch.org/docs/2.8/notes/randomness.html): seed와 결정적 연산 제어를 구분한다.
- [PyTorch2.8 FlashAttention backward 구현](https://github.com/pytorch/pytorch/blob/v2.8.0/aten/src/ATen/native/transformers/cuda/attention_backward.cu#L97-L106): 엄격한 deterministic flag가 별도 backward 경로를 선택한다. 실제 모델에서 선택됐는지는 실험으로 확인한다.
- [SDPA 문서](https://docs.pytorch.org/docs/2.8/generated/torch.nn.functional.scaled_dot_product_attention.html): backend별 수치 차이와 backend 제어를 설명한다.
- [기존 고정 P0/V8 평가 코드](https://github.com/jang2296/MMDL/tree/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1).

카카오톡용 요약은 검증 결과를 바탕으로 별도 작성했다. 외부 메시지를 자동으로 보내지 않았다.

<!-- VERIFIED_RESULTS -->
## 실제 검증 결과

### 원인: 기본 FlashAttention backward의 dQ가 반복 불일치

실제 첫 decoder attention은 `aten::_scaled_dot_product_flash_attention_backward`를 사용했다. 첫4문항의 실제 모델 기록에는 이 backward 호출144회가 있다. 첫 layer의 Q/K/V와 들어오는 gradient를 고정한 국소 재실행에서 다음을 확인했다.

| 조건 · 각3회 | 서로 다른 forward 결과 | 서로 다른 gradient | dQ/dK/dV 각각의 서로 다른 결과 수 |
|---|---:|---:|---|
| 기본 자동 FlashAttention | 1 | 3 | 3 / 1 / 1 |
| 같은 FlashAttention + 엄격한 deterministic flag | 1 | 1 | 1 / 1 / 1 |
| math SDPA 참조 | 1 | 1 | 1 / 1 / 1 |

입력 텐서와 들어오는 gradient의 비트, 원래 strides가 유지됐다. 기본/엄격한 FlashAttention의 forward 결과도 서로 같았다. 기본 조건의 dQ 최대 절대 차이는 `2.384185791015625e-07`이었고 엄격한 flag에서는0이었다. 따라서 **이 실제 실행 경로에서 확인한 비결정성 원인 하나는 FlashAttention backward의 dQ 계산**이다. 특정 attention 연산의 국소 실험으로 모든 가능한 학습 비결정성 원인이 이것뿐이라고 단정하지 않는다.

이후 두 새 프로세스의 전체 첫4문항 preflight에서 초기값·입력·logits·logp·첫 gradient·norm이 모두 같았다. 선택 정책은 **`strict_auto`**이며 math fallback은 사용하지 않았다. 첫 gradient norm은 두 preflight 및 실제 학습A/B 모두 `1.3743702173233032`였다.

주의: 국소 SDPA 비교의 첫 두 조건은 flag만 바꿨다. 반면 **전체 학습의 엄격한 정책은 TF32/저정밀 reduction/cuBLAS workspace도 함께 통제**한다. 전체 legacy/strict 비교에서는 같은 초기값·같은 입력에도 첫 logp가 달랐다. 이번 결과는 새로 명시한 수치 실행 조건 아래의 반복 일치이며, 과거493점 학습의 전체 forward 수치를 그대로 복원했다는 주장은 아니다.

### 전체48개 독립 학습 A/B

| 검사 | 결과 |
|---|---|
| 고유 학습자료·초기 LoRA | 48개 입력 및144개 초기 텐서 일치 |
| epoch 순서 | 3407/3408 순서 일치 |
| forward | 각96개 logp 기록 및 첫4개의 전체 마무리 logits 일치 |
| loss | 24/24업데이트 동일 |
| clipping 전 gradient 전체 해시 | 24/24업데이트 동일 |
| gradient norm | 24/24업데이트 동일 |
| 최종 실제 LoRA 텐서 | **144/144 비트 단위 일치** |
| 실제 adapter 파일 | 전체 바이트 및SHA256 동일 |
| 재로딩·학습 변화 | 각각재로딩 일치·유한값·144개 텐서 변화 확인 |
| merged 가중치 | safetensors 파일 해시 일치 |

공통 어댑터 SHA256: `90f0afaf72f22c622fd7e533514b02efd0b650d07589ff5773f6864b952188f8`.

입력48개와 마무리 token IDs는 원래 자료 그대로다. A/B는 새 프로세스에서 원본Qwen을 각각 로딩해 초기화했다. 첫4문항 사전 검사는 업데이트0회이며 실제 전체 학습은 각각24업데이트다. 실제 어댑터 파일의 내부144개 FP32 버퍼를 로컬에서 직접 읽어 원격 fingerprint와 대조했고 비트 단위 동일성을 다시 확인했다.

### 24문항 자유 생성

| 실행 | V8 정답 | 평균 토큰 | 중앙값 | 2048도달 | NO_PARSE | generate 시간 |
|---|---:|---:|---:|---:|---:|---:|
| A_1 | 13/24 | 1139.4 | 754.5 | 10/24 | 10 | 223.50초 |
| B_1 | 13/24 | 1139.4 | 754.5 | 10/24 | 10 | 221.07초 |

**원문·토큰열·종료 사유24/24개 일치, 최종 추출 답변24/24개 일치.** 이는두 모델의 출력 일치율이며 정답률100%라는 뜻이 아니다. 위 표의 정답 수와 구분한다. 각24고유ID·입력 해시·실제 prompt token IDs 해시·seed가 기존잠금과 일치했고 누락·중복이 없었다. 원격 별도 프로세스와 로컬에서 저장 응답48개를 같은 고정V8로 각각 재채점해 모든 채점 필드가 일치했다.

generate 시간은 엔진 로딩·설치·학습·백업을 제외한 호출 벽시계다. 기존 실행과 정밀한 속도 벤치마크로 비교하지 않는다. 새로운 모델 우열을 고르거나900성능을 추정하기 위해 이 표본을 사용하지 않았다.

### 전수24문항 확인

A/B의 정오·원문·토큰·종료 사유가 모두 같아 공통 항목과 일치 여부를 표시한다. 원문과 전체 token IDs는 보존한 `inference/A_1.json`, `inference/B_1.json`에 있다.

| ID | 공통 추출 답 | V8 정오 | 토큰 | 종료 | 파싱 | 원문·토큰 일치 |
|---|---|---|---:|---|---|---|
| validation_Accounting_1 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_10 | A | 정답 | 559 | stop | PARSED | 일치 |
| validation_Accounting_11 | A | 정답 | 475 | stop | PARSED | 일치 |
| validation_Accounting_12 | A | 정답 | 107 | stop | PARSED | 일치 |
| validation_Accounting_13 | C | 정답 | 577 | stop | PARSED | 일치 |
| validation_Accounting_14 | B | 정답 | 103 | stop | PARSED | 일치 |
| validation_Accounting_15 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_16 | C | 정답 | 194 | stop | PARSED | 일치 |
| validation_Accounting_17 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_18 | D | 정답 | 172 | stop | PARSED | 일치 |
| validation_Accounting_19 | C | 정답 | 564 | stop | PARSED | 일치 |
| validation_Accounting_2 | C | 정답 | 1576 | stop | PARSED | 일치 |
| validation_Accounting_20 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_21 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_22 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_23 | B | 정답 | 605 | stop | PARSED | 일치 |
| validation_Accounting_24 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_25 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_26 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_27 | C | 정답 | 174 | stop | PARSED | 일치 |
| validation_Accounting_28 | None | 오답 | 2048 | length | NO_PARSE | 일치 |
| validation_Accounting_29 | B | 정답 | 254 | stop | PARSED | 일치 |
| validation_Accounting_3 | B | 정답 | 904 | stop | PARSED | 일치 |
| validation_Accounting_30 | B | 오답 | 602 | stop | PARSED | 일치 |

### 실행·비용·보존

- driver 관측: `2026-11-18T23:13:34+09:00` → `2026-11-18T23:57:25+09:00`. 약43.8분이며 설치·다운로드·진단·중간 백업 확인 대기를 포함한다. 최종 백업·해제 확인은 이후다.
- L4 표시 요율1.94CU/h. 연결 전36.04CU → 종료 후34.63CU, 표시상 약1.41CU 감소다. 반올림·설치·백업 대기를 포함하며 학습만의 정확한 비용이나 금액으로 해석하지 않는다.
- 최종 활성 세션0개, 사용률0CU/h를 별도로 관측했다. 회수 목적으로 GPU를 다시 켜지 않았다.
- 5개 증분ZIP과ready marker 전부 보존했다. 각ZIP은 실제 Drive 업로드→회수 바이트SHA256·CRC·모든 내부 파일해시를 검증했다. 실제A/B 어댑터·수치추적·프로파일 연산명·원문48개·비교JSON·종료 기록을 보존했다.
- 로컬 검사: 내장소스/자료SHA 일치·사전검사 실패 차단·진단/최종 packet 복구 및 손상거부3개 검사를 통과했다. 실제GPU 결과는 별도로 위 항목을 검증했다.

| 순서 | 단계 | bytes | ZIP SHA256 |
|---:|---|---:|---|
| 1 | diagnosis | 415,843 | `eac36dba3747688227a8ff49329ad63136216e4549288e02c596a046a1444949` |
| 2 | train_A | 11,161,338 | `2bcdb7c06f8e2547c77ef383b57e9481eed7b2318a726f2bf340171213ef4bb5` |
| 3 | train_B | 11,163,272 | `3ff6885908cbc35de8f746bc625234b1df3a96a0ce657eeda48c0e7e3290a60c` |
| 4 | compare | 163,864 | `965cfe183ca0b56e9c7c47a6a6370b113b7d1254d31bcab00b5a19a542499c6d` |
| 5 | final | 1,347 | `ed40e010200a0f1b7ccaf0f03e9534b96aa56a37b849b869db962320ea28b05a` |

### 결론과 적용 범위

**같은 고정 환경에서 마무리SFT를 다시 학습했을 때 동일 가중치와 동일24문항 출력을 얻는 절차를 두 독립 실행으로 확인했다.** 기본FlashAttention backward의 비결정성을 실제 입력으로 확인했고, 엄격한 조건에서24회 전체gradient와 최종 가중치까지 같았다.

이 결과는 성능 상승 실험이 아니다. 과거493/900 어댑터 복원·전체900점수 재현·다른GPU/드라이버/버전·다른배치구성의 동일성은 확인하지 않았다. 기존 MMMU validation을 여러 번 분석했으므로 미사용 최종test로 설명하지 않는다. 고정된 새 어댑터의 전체900 정확도는 별도 평가가 필요하다.

이 결과를 재현할 때는 `control.json`의 **strict_auto**와 실제버전·환경·같은자료·같은요청창을 확인한다. 향후 math fallback이 선택된 실행은 이 결과와 같은 조건으로 합치지 않는다. 시드·패키지명만 같다는 이유로 다른실행의 같은 가중치를 보장하지 않는다.

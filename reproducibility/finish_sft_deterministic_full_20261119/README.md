# 재현된 마무리 SFT · 전체900문항 평가

**원본 478/900 → 재현 LoRA 487/900 (+9개, +1.00%p). 이전 마무리 SFT 493점 대비 -6개.**

관측 정답 수는 이전493점보다 6개 낮았다. 이 차이만으로 통계적 열등성을 단정하지 않는다. 이번에는 추가 학습 없이 앞서 두 독립 학습에서 동일성이 확인된 실제 가중치를 평가했다. 여기서 점수 유지 여부는 이번 관측 정답 수의 비교이며, 사전에 정한 동등성·비열등성 검정의 결론은 아니다. 같은 고정 조건으로 이번 원본888개와 중단 뒤 별도 프로세스에서 평가한 마지막12개를 합쳤다. 원본900개를 한 프로세스에서 중단 없이 실행한 결과로 표현하지 않는다. 이전493점 모델과 이번 가중치가 동일하다는 뜻은 아니다.

## 전체 결과

| 조건 | 정답 | 정확도 | 평균 토큰 | 중앙값 | 상한 도달 | 추출 실패 |
|---|---:|---:|---:|---:|---:|---:|
| 이전 통제 원본 | 478/900 | 53.11% | 863.4 | 447 | 230 | 228 |
| 이전 마무리 SFT | 493/900 | 54.78% | 794.2 | 405.5 | 201 | 205 |
| 이번 원본 Qwen | 478/900 | 53.11% | 863.4 | 447 | 230 | 228 |
| 이번 재현 LoRA | 487/900 | 54.11% | 795.2 | 398.5 | 207 | 207 |

초기의479/900은 별도 역사적 원본 기록이다. 이번의 직접 통제 비교는 고정한 동일 조건의 원본과 재현 LoRA다. 원본만888개 이후 별도 프로세스로12개를 재개했다. 이전 통제 원본478점·마무리SFT493점은 검증된 과거 compact 기록과 연결했다.

원본 재실행과 과거 원본의 일치: 추출 답변 900/900, 정오 900/900, 생성 토큰 개수 900/900. 과거 원문·실제 토큰열이 전수 확보된 것은 아니므로 그 비트 동일성은 비교하지 않았다.

## 무엇을 얻고 잃었나

- 계속 정답 431개 / 추가 정답 56개 / 잃은 정답 47개 / 계속 오답 366개.
- 원본 정답 유지율 90.17%.
- paired McNemar exact p=0.43069; 문항별 정오 차이의 근사95% CI [-1.21, +3.21]%p.
- 이전493점과 비교한 추가 정답 36개, 잃은 정답 42개.

이번 원본 대비 추가 정답 중 28개는 원본의 추출 실패가 사라진 경우, 28개는 양쪽 모두 파싱된 상태에서 답이 정답으로 바뀐 경우다. 잃은 정답 중 22개는 새 추출 실패, 25개는 파싱된 답 자체가 오답으로 바뀌었다. 이는 출력 상태와 정오의 구분이며, 전수 풀이 논리 개선을 판정한 결과가 아니다.

전체 정답 차이의95% CI에0이 포함되고 McNemar p가0.05보다 크다. 이번 한 실행으로 안정적인 전체 성능 향상을 입증하거나 이전493점 모델과의 동등성을 입증했다고 해석하지 않는다.

## 기술·공학210문항

현재 원본 56/210 → 재현 LoRA 63/210. 이전 마무리SFT는 69/210이었다. 이번 원본 대비 추가 정답은 18개, 잃은 정답은 11개다. 전체 순증9개 중7개가 이210개 부분집합에서 관측됐으며, 나머지690개는 원본422개→이번424개다. 이 숫자 분해는 원인 규명이 아니다.

선택 분야는 기존 manifest 그대로다: Agriculture, Architecture_and_Engineering, Computer_Science, Electronics, Energy_and_Power, Materials, Mechanical_Engineering. 분야마다30개이며30개 분야의 전체 표와4그룹 전수ID 목록은 비교JSON에 저장했다. 분야별 차이는 작은 표본의 탐색 결과이며 다중 비교를 고려해야 한다. 원본의 마지막12개는 재개 실행임을 함께 고려한다.

## 저장 응답을 직접 살펴본 세 사례

- **validation_Accounting_19** · 2048 → 564토큰. 원본 끝부분은 C/$12를 이미 후보로 냈지만 간접재료 해석을 다시 검토하다2048에서 잘렸다. SFT는564토큰에서C/$12를 명시하고 종료했다. 완료 방식이 나아진 사례이며 새 지식을 습득했다는 증거로 해석하지 않는다.

- **validation_Accounting_1** · 389 → 2048토큰. 원본은389토큰에서B/$7로 종료했다. SFT는 간접재료 $3를 포함해 $10을 계산하고, 보기와 맞지 않는 해석을 반복하다 2048에서 잘렸다. 원문에서$7은 보기 열거로 등장하며, 정답을 완성해놓고 멈추지 않은 사례로 단정하지 않는다.

- **validation_Art_21** · 182 → 181토큰. 원본C/182토큰에서SFT B/181토큰으로 답이 바뀌었다. 둘 다 파싱됐지만 제공 정답 C 기준으로 SFT만 틀렸다. 길이가 비슷하게 짧아도 답을 잃을 수 있다. 원본 그림을 다시 판독해 미술사적 근거를 검증한 것은 아니다.

이 세 사례는 저장된 응답의 시작·끝을 직접 읽어 설명했다. 도면·그림을 새로 판독하거나900개 풀이의 타당성을 전수 수작업 검토한 결과는 아니다.

## 고정한 조건과 실제 가중치

- Qwen3-VL-4B-Instruct revision `ebb281ec70b05090aa6165b016eac8ec08e71b17`; MMMU validation revision `98e6ac0cb9b7b2cd2c991b85a50762edc4aedc68`.
- P0·기존 이미지 전처리·2048토큰·V8·engine3407·기존 문항별SHA256 seed·MP0·vLLM0.11.0. 실제 요청창24/동시요청8/context12288, SFT900은 하나의 새 프로세스이며 원본은888개와 재개12개로 나뉜다.
- `90f0afaf72f22c622fd7e533514b02efd0b650d07589ff5773f6864b952188f8`: 두 독립 학습에서 비트 단위로 같았던 실제 LoRA.144개 텐서와 병합된 inference 가중치 파일 SHA가 이전24문항 검증값과 일치했다.
- 추가 학습0회, 강제 마무리 문구·재호출·정답 선택/필터 없이 문항당1회 자유 생성.900문항은 학습하지 않았다.
- 원래 학습은 자체 합성48개의 검산된 마무리+EOS에만 CE loss를 주는 Q/V LoRA SFT다. 학습자료 SHA256은 `1ca52b224f3c03dfae2d3297d9bfc8a0e563936afc117293e9d5f2e65cc09070`, 시드3407·2epoch/24update·감독 토큰 노출7,610개다. 이번 가중치는 strict_auto 수치 실행 조건으로 독립 학습A/B가 일치한 새 모델이며, 과거493점 어댑터의 전체 수치를 복원한 모델은 아니다. 이번900평가에서는 학습하지 않았다.

## 검증과 해석 범위

- 현재 두 조건 각각900개 고유ID, 입력/실제 prompt token hash/seed 확인. 원본888개는 이전135분 제한까지 저장됐고, 마지막12개만 동일한 창 구성으로 새 프로세스에서 재개했다. 누락·중복 없이 원문·토큰열·종료 사유를 보존했다.
- 원격 별도 프로세스와 로컬 고정V8로1800응답을 독립 재채점하고 모든 채점 필드가 일치했다.
- 전체19개 증분ZIP을 업로드하고 실제 Drive에서 다시 회수해 전체 바이트·SHA256·CRC·모든 내부 파일 해시를 확인했다. 마지막ZIP 하나로 복구되지 않는다.
- 과거493점의 원문이 이 비교자료에 모두 회수된 것은 아니다. 그 조건과의 문항 비교는 당시 검증된 compact 기록이며 과거 원문의 원인을 새로 수작업 검토했다고 주장하지 않는다.
- 앞선24문항과 이번 첫24문항의 원문·토큰·종료 사유 일치는 24/24. 새LoRA의 전체900문항 원문·토큰열 반복 재현성이나 배치 불변성은 이번 검사 범위가 아니다.
- 동일 시드라도 GPU/드라이버/라이브러리/배치에 따른 변동 가능성이 남는다. vLLM0.11.0은 BATCH_INVARIANT를 지원하지 않는다.
- 문항별 CI/p값은 학습·실행 변동성을 포함하지 않는다. MMMU validation을 여러 번 개발에 사용했으므로 미사용 최종test의 일반화 성능으로 설명하지 않는다.

## 중단과 부분 재개

초기 원본 평가는 135분 제한이 백업 확인 대기를 포함하면서 888개에서 SIGTERM으로 끝났다. 해당888개를 다시 생성하지 않고 마지막12개만 복원된 실행의 창38로 평가했다. LoRA는 아직 시작되지 않았으므로900개 전부 하나의 새 프로세스로 실행했다. 재개 코드는 같은 창/시드/전처리/V8/토큰 상한을 유지하며, 응답 재개와 시간 제한 수정만 분리 기록했다. 원본의 완전한 단일 프로세스900 재현성을 입증했다는 뜻은 아니다. 중단 전후 환경과 과거900 기록의 일치는 비교JSON에 저장했다.

## 시간과 비용

모델 호출 벽시계: 원본 7026.89초, 재현 LoRA 6569.17초. 설치·자료 전처리·엔진 로딩·백업 대기는 제외한다. 정확한 계산만의 비용이나 금액으로 환산하지 않는다.

관측한 L4 사용률은1.94CU/h였다. 이번 작업 전체의 표시상 잔액 감소는 약8.99CU이며 준비·설치·백업 대기·초기 중단 후 재개와 반올림을 포함한다. 학습만의 정확한 비용이 아니다. 최종 활성 세션0/사용률0을 확인했다.

## 근거 파일

- `comparison.json`: 전체/분야/질문유형 통계·4그룹 전수목록·검증.
- `per-question-comparison.json`:900개 문항의 현재 원문·토큰·정답·추출·정오·근거파일 및 과거 compact 기록.
- `artifacts/responses/`: 현재 두 조건의38개씩 저장 창.
- `run_state.json`, `checkpoints/`: 실행 상태와19개 증분백업/ready marker.
- [이전 재현성 검증 코드와 결과](https://github.com/dust9826/mmdl-colab-baseline/tree/a8921a1b96aca885fbe6023199d21a6f3b952f95/reproducibility/finish_sft_deterministic_20261118).
- [고정 평가 코드](https://github.com/jang2296/MMDL/tree/f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1).

## 30개 분야별 정답 수

| 분야 | n | 이번 원본 | 이전 SFT | 이번 재현 SFT | 추가 정답 | 잃은 정답 | 순증감 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Accounting | 30 | 15 | 15 | 16 | 3 | 2 | +1 |
| Agriculture | 30 | 13 | 17 | 17 | 4 | 0 | +4 |
| Architecture_and_Engineering | 30 | 4 | 4 | 5 | 1 | 0 | +1 |
| Art | 30 | 19 | 18 | 18 | 0 | 1 | -1 |
| Art_Theory | 30 | 25 | 25 | 25 | 1 | 1 | +0 |
| Basic_Medical_Science | 30 | 20 | 22 | 21 | 2 | 1 | +1 |
| Biology | 30 | 15 | 18 | 17 | 4 | 2 | +2 |
| Chemistry | 30 | 9 | 10 | 9 | 2 | 2 | +0 |
| Clinical_Medicine | 30 | 22 | 19 | 20 | 2 | 4 | -2 |
| Computer_Science | 30 | 16 | 15 | 13 | 1 | 4 | -3 |
| Design | 30 | 22 | 23 | 24 | 2 | 0 | +2 |
| Diagnostics_and_Laboratory_Medicine | 30 | 10 | 9 | 9 | 1 | 2 | -1 |
| Economics | 30 | 25 | 23 | 22 | 0 | 3 | -3 |
| Electronics | 30 | 6 | 8 | 7 | 1 | 0 | +1 |
| Energy_and_Power | 30 | 5 | 9 | 8 | 4 | 1 | +3 |
| Finance | 30 | 18 | 15 | 18 | 1 | 1 | +0 |
| Geography | 30 | 15 | 15 | 14 | 2 | 3 | -1 |
| History | 30 | 21 | 23 | 21 | 2 | 2 | +0 |
| Literature | 30 | 24 | 24 | 24 | 0 | 0 | +0 |
| Manage | 30 | 17 | 15 | 16 | 0 | 1 | -1 |
| Marketing | 30 | 22 | 25 | 24 | 4 | 2 | +2 |
| Materials | 30 | 7 | 9 | 7 | 3 | 3 | +0 |
| Math | 30 | 14 | 12 | 14 | 1 | 1 | +0 |
| Mechanical_Engineering | 30 | 5 | 7 | 6 | 4 | 3 | +1 |
| Music | 30 | 4 | 7 | 4 | 1 | 1 | +0 |
| Pharmacy | 30 | 18 | 22 | 21 | 5 | 2 | +3 |
| Physics | 30 | 21 | 20 | 21 | 2 | 2 | +0 |
| Psychology | 30 | 23 | 24 | 24 | 1 | 0 | +1 |
| Public_Health | 30 | 24 | 22 | 24 | 0 | 0 | +0 |
| Sociology | 30 | 19 | 18 | 18 | 2 | 3 | -1 |

## 추가 정답과 잃은 정답의 출력 상태

아래는 같은 V8의 출력 상태를 자동 집계한 것으로, 이미지 판독이나 풀이 논리를 전수 수작업 검토한 결과는 아니다. 상한 도달 수는 파싱 범주와 겹칠 수 있다.

| 구분 | n | 원본 추출 실패→SFT 파싱 | 원본 파싱→SFT 추출 실패 | 둘 다 파싱 | 원본2048 도달 | SFT2048 도달 |
|---|---:|---:|---:|---:|---:|---:|
| 추가 정답 | 56 | 28 | 0 | 28 | 25 | 3 |
| 잃은 정답 | 47 | 0 | 22 | 25 | 2 | 22 |

## 네 그룹 전수 ID

각 그룹은 이번 원본 → 이번 재현 SFT 기준이다. 네 목록을 합치면900개 고유ID이며, 추가 정답과 잃은 정답을 함께 공개한다.

<details>
<summary>계속 정답 · 431개</summary>

- `validation_Accounting_10`
- `validation_Accounting_11`
- `validation_Accounting_12`
- `validation_Accounting_13`
- `validation_Accounting_14`
- `validation_Accounting_16`
- `validation_Accounting_18`
- `validation_Accounting_23`
- `validation_Accounting_27`
- `validation_Accounting_29`
- `validation_Accounting_3`
- `validation_Accounting_8`
- `validation_Accounting_9`
- `validation_Agriculture_1`
- `validation_Agriculture_11`
- `validation_Agriculture_14`
- `validation_Agriculture_16`
- `validation_Agriculture_18`
- `validation_Agriculture_19`
- `validation_Agriculture_24`
- `validation_Agriculture_25`
- `validation_Agriculture_26`
- `validation_Agriculture_28`
- `validation_Agriculture_29`
- `validation_Agriculture_30`
- `validation_Agriculture_6`
- `validation_Architecture_and_Engineering_24`
- `validation_Architecture_and_Engineering_25`
- `validation_Architecture_and_Engineering_28`
- `validation_Architecture_and_Engineering_5`
- `validation_Art_1`
- `validation_Art_10`
- `validation_Art_13`
- `validation_Art_17`
- `validation_Art_2`
- `validation_Art_22`
- `validation_Art_24`
- `validation_Art_25`
- `validation_Art_27`
- `validation_Art_28`
- `validation_Art_29`
- `validation_Art_3`
- `validation_Art_30`
- `validation_Art_4`
- `validation_Art_5`
- `validation_Art_6`
- `validation_Art_7`
- `validation_Art_8`
- `validation_Art_Theory_1`
- `validation_Art_Theory_10`
- `validation_Art_Theory_11`
- `validation_Art_Theory_13`
- `validation_Art_Theory_15`
- `validation_Art_Theory_16`
- `validation_Art_Theory_18`
- `validation_Art_Theory_19`
- `validation_Art_Theory_2`
- `validation_Art_Theory_20`
- `validation_Art_Theory_21`
- `validation_Art_Theory_22`
- `validation_Art_Theory_23`
- `validation_Art_Theory_24`
- `validation_Art_Theory_26`
- `validation_Art_Theory_27`
- `validation_Art_Theory_28`
- `validation_Art_Theory_29`
- `validation_Art_Theory_30`
- `validation_Art_Theory_4`
- `validation_Art_Theory_6`
- `validation_Art_Theory_7`
- `validation_Art_Theory_8`
- `validation_Art_Theory_9`
- `validation_Basic_Medical_Science_1`
- `validation_Basic_Medical_Science_13`
- `validation_Basic_Medical_Science_15`
- `validation_Basic_Medical_Science_16`
- `validation_Basic_Medical_Science_19`
- `validation_Basic_Medical_Science_2`
- `validation_Basic_Medical_Science_20`
- `validation_Basic_Medical_Science_24`
- `validation_Basic_Medical_Science_26`
- `validation_Basic_Medical_Science_27`
- `validation_Basic_Medical_Science_28`
- `validation_Basic_Medical_Science_29`
- `validation_Basic_Medical_Science_3`
- `validation_Basic_Medical_Science_30`
- `validation_Basic_Medical_Science_4`
- `validation_Basic_Medical_Science_5`
- `validation_Basic_Medical_Science_7`
- `validation_Basic_Medical_Science_8`
- `validation_Basic_Medical_Science_9`
- `validation_Biology_12`
- `validation_Biology_13`
- `validation_Biology_15`
- `validation_Biology_16`
- `validation_Biology_18`
- `validation_Biology_19`
- `validation_Biology_21`
- `validation_Biology_24`
- `validation_Biology_25`
- `validation_Biology_26`
- `validation_Biology_4`
- `validation_Biology_5`
- `validation_Biology_8`
- `validation_Chemistry_1`
- `validation_Chemistry_10`
- `validation_Chemistry_11`
- `validation_Chemistry_15`
- `validation_Chemistry_16`
- `validation_Chemistry_18`
- `validation_Chemistry_27`
- `validation_Clinical_Medicine_1`
- `validation_Clinical_Medicine_10`
- `validation_Clinical_Medicine_12`
- `validation_Clinical_Medicine_13`
- `validation_Clinical_Medicine_17`
- `validation_Clinical_Medicine_19`
- `validation_Clinical_Medicine_20`
- `validation_Clinical_Medicine_21`
- `validation_Clinical_Medicine_22`
- `validation_Clinical_Medicine_23`
- `validation_Clinical_Medicine_26`
- `validation_Clinical_Medicine_27`
- `validation_Clinical_Medicine_28`
- `validation_Clinical_Medicine_29`
- `validation_Clinical_Medicine_3`
- `validation_Clinical_Medicine_4`
- `validation_Clinical_Medicine_6`
- `validation_Clinical_Medicine_9`
- `validation_Computer_Science_13`
- `validation_Computer_Science_15`
- `validation_Computer_Science_17`
- `validation_Computer_Science_21`
- `validation_Computer_Science_24`
- `validation_Computer_Science_27`
- `validation_Computer_Science_29`
- `validation_Computer_Science_3`
- `validation_Computer_Science_30`
- `validation_Computer_Science_5`
- `validation_Computer_Science_6`
- `validation_Computer_Science_9`
- `validation_Design_10`
- `validation_Design_11`
- `validation_Design_16`
- `validation_Design_17`
- `validation_Design_18`
- `validation_Design_19`
- `validation_Design_20`
- `validation_Design_21`
- `validation_Design_22`
- `validation_Design_23`
- `validation_Design_24`
- `validation_Design_25`
- `validation_Design_26`
- `validation_Design_27`
- `validation_Design_28`
- `validation_Design_30`
- `validation_Design_4`
- `validation_Design_5`
- `validation_Design_6`
- `validation_Design_7`
- `validation_Design_8`
- `validation_Design_9`
- `validation_Diagnostics_and_Laboratory_Medicine_11`
- `validation_Diagnostics_and_Laboratory_Medicine_12`
- `validation_Diagnostics_and_Laboratory_Medicine_24`
- `validation_Diagnostics_and_Laboratory_Medicine_25`
- `validation_Diagnostics_and_Laboratory_Medicine_27`
- `validation_Diagnostics_and_Laboratory_Medicine_28`
- `validation_Diagnostics_and_Laboratory_Medicine_29`
- `validation_Diagnostics_and_Laboratory_Medicine_4`
- `validation_Economics_10`
- `validation_Economics_11`
- `validation_Economics_12`
- `validation_Economics_13`
- `validation_Economics_14`
- `validation_Economics_16`
- `validation_Economics_17`
- `validation_Economics_18`
- `validation_Economics_19`
- `validation_Economics_2`
- `validation_Economics_20`
- `validation_Economics_21`
- `validation_Economics_22`
- `validation_Economics_25`
- `validation_Economics_27`
- `validation_Economics_29`
- `validation_Economics_3`
- `validation_Economics_4`
- `validation_Economics_6`
- `validation_Economics_7`
- `validation_Economics_8`
- `validation_Economics_9`
- `validation_Electronics_12`
- `validation_Electronics_15`
- `validation_Electronics_20`
- `validation_Electronics_23`
- `validation_Electronics_3`
- `validation_Electronics_8`
- `validation_Energy_and_Power_11`
- `validation_Energy_and_Power_24`
- `validation_Energy_and_Power_27`
- `validation_Energy_and_Power_30`
- `validation_Finance_1`
- `validation_Finance_11`
- `validation_Finance_12`
- `validation_Finance_13`
- `validation_Finance_16`
- `validation_Finance_17`
- `validation_Finance_18`
- `validation_Finance_19`
- `validation_Finance_2`
- `validation_Finance_22`
- `validation_Finance_24`
- `validation_Finance_26`
- `validation_Finance_27`
- `validation_Finance_3`
- `validation_Finance_4`
- `validation_Finance_6`
- `validation_Finance_7`
- `validation_Geography_12`
- `validation_Geography_15`
- `validation_Geography_16`
- `validation_Geography_18`
- `validation_Geography_19`
- `validation_Geography_21`
- `validation_Geography_22`
- `validation_Geography_25`
- `validation_Geography_26`
- `validation_Geography_28`
- `validation_Geography_29`
- `validation_Geography_3`
- `validation_History_1`
- `validation_History_12`
- `validation_History_14`
- `validation_History_15`
- `validation_History_16`
- `validation_History_17`
- `validation_History_18`
- `validation_History_19`
- `validation_History_20`
- `validation_History_21`
- `validation_History_22`
- `validation_History_24`
- `validation_History_25`
- `validation_History_26`
- `validation_History_27`
- `validation_History_28`
- `validation_History_29`
- `validation_History_3`
- `validation_History_4`
- `validation_Literature_1`
- `validation_Literature_10`
- `validation_Literature_11`
- `validation_Literature_12`
- `validation_Literature_13`
- `validation_Literature_15`
- `validation_Literature_16`
- `validation_Literature_17`
- `validation_Literature_19`
- `validation_Literature_2`
- `validation_Literature_20`
- `validation_Literature_22`
- `validation_Literature_23`
- `validation_Literature_25`
- `validation_Literature_27`
- `validation_Literature_29`
- `validation_Literature_3`
- `validation_Literature_30`
- `validation_Literature_4`
- `validation_Literature_5`
- `validation_Literature_6`
- `validation_Literature_7`
- `validation_Literature_8`
- `validation_Literature_9`
- `validation_Manage_1`
- `validation_Manage_10`
- `validation_Manage_11`
- `validation_Manage_14`
- `validation_Manage_15`
- `validation_Manage_16`
- `validation_Manage_17`
- `validation_Manage_2`
- `validation_Manage_21`
- `validation_Manage_25`
- `validation_Manage_28`
- `validation_Manage_29`
- `validation_Manage_30`
- `validation_Manage_5`
- `validation_Manage_8`
- `validation_Manage_9`
- `validation_Marketing_1`
- `validation_Marketing_10`
- `validation_Marketing_11`
- `validation_Marketing_16`
- `validation_Marketing_17`
- `validation_Marketing_19`
- `validation_Marketing_2`
- `validation_Marketing_20`
- `validation_Marketing_21`
- `validation_Marketing_22`
- `validation_Marketing_24`
- `validation_Marketing_25`
- `validation_Marketing_26`
- `validation_Marketing_27`
- `validation_Marketing_29`
- `validation_Marketing_3`
- `validation_Marketing_30`
- `validation_Marketing_5`
- `validation_Marketing_6`
- `validation_Marketing_7`
- `validation_Materials_15`
- `validation_Materials_23`
- `validation_Materials_5`
- `validation_Materials_8`
- `validation_Math_1`
- `validation_Math_10`
- `validation_Math_11`
- `validation_Math_14`
- `validation_Math_18`
- `validation_Math_21`
- `validation_Math_23`
- `validation_Math_24`
- `validation_Math_27`
- `validation_Math_29`
- `validation_Math_30`
- `validation_Math_6`
- `validation_Math_7`
- `validation_Mechanical_Engineering_24`
- `validation_Mechanical_Engineering_6`
- `validation_Music_10`
- `validation_Music_12`
- `validation_Music_26`
- `validation_Pharmacy_10`
- `validation_Pharmacy_11`
- `validation_Pharmacy_14`
- `validation_Pharmacy_15`
- `validation_Pharmacy_16`
- `validation_Pharmacy_2`
- `validation_Pharmacy_22`
- `validation_Pharmacy_24`
- `validation_Pharmacy_25`
- `validation_Pharmacy_29`
- `validation_Pharmacy_3`
- `validation_Pharmacy_5`
- `validation_Pharmacy_6`
- `validation_Pharmacy_7`
- `validation_Pharmacy_8`
- `validation_Pharmacy_9`
- `validation_Physics_11`
- `validation_Physics_14`
- `validation_Physics_16`
- `validation_Physics_17`
- `validation_Physics_21`
- `validation_Physics_22`
- `validation_Physics_23`
- `validation_Physics_24`
- `validation_Physics_25`
- `validation_Physics_26`
- `validation_Physics_27`
- `validation_Physics_28`
- `validation_Physics_29`
- `validation_Physics_3`
- `validation_Physics_30`
- `validation_Physics_4`
- `validation_Physics_5`
- `validation_Physics_6`
- `validation_Physics_8`
- `validation_Psychology_1`
- `validation_Psychology_10`
- `validation_Psychology_11`
- `validation_Psychology_13`
- `validation_Psychology_14`
- `validation_Psychology_15`
- `validation_Psychology_16`
- `validation_Psychology_17`
- `validation_Psychology_18`
- `validation_Psychology_19`
- `validation_Psychology_2`
- `validation_Psychology_21`
- `validation_Psychology_22`
- `validation_Psychology_23`
- `validation_Psychology_25`
- `validation_Psychology_27`
- `validation_Psychology_28`
- `validation_Psychology_29`
- `validation_Psychology_3`
- `validation_Psychology_4`
- `validation_Psychology_5`
- `validation_Psychology_7`
- `validation_Psychology_8`
- `validation_Public_Health_10`
- `validation_Public_Health_12`
- `validation_Public_Health_13`
- `validation_Public_Health_14`
- `validation_Public_Health_15`
- `validation_Public_Health_16`
- `validation_Public_Health_17`
- `validation_Public_Health_18`
- `validation_Public_Health_19`
- `validation_Public_Health_2`
- `validation_Public_Health_20`
- `validation_Public_Health_21`
- `validation_Public_Health_22`
- `validation_Public_Health_23`
- `validation_Public_Health_25`
- `validation_Public_Health_26`
- `validation_Public_Health_27`
- `validation_Public_Health_29`
- `validation_Public_Health_3`
- `validation_Public_Health_4`
- `validation_Public_Health_5`
- `validation_Public_Health_6`
- `validation_Public_Health_7`
- `validation_Public_Health_8`
- `validation_Sociology_13`
- `validation_Sociology_14`
- `validation_Sociology_16`
- `validation_Sociology_17`
- `validation_Sociology_18`
- `validation_Sociology_19`
- `validation_Sociology_2`
- `validation_Sociology_22`
- `validation_Sociology_26`
- `validation_Sociology_28`
- `validation_Sociology_29`
- `validation_Sociology_30`
- `validation_Sociology_4`
- `validation_Sociology_6`
- `validation_Sociology_7`
- `validation_Sociology_8`

</details>

<details>
<summary>추가 정답 · 56개</summary>

- `validation_Accounting_19`
- `validation_Accounting_2`
- `validation_Accounting_7`
- `validation_Agriculture_10`
- `validation_Agriculture_2`
- `validation_Agriculture_23`
- `validation_Agriculture_7`
- `validation_Architecture_and_Engineering_11`
- `validation_Art_Theory_14`
- `validation_Basic_Medical_Science_18`
- `validation_Basic_Medical_Science_21`
- `validation_Biology_11`
- `validation_Biology_2`
- `validation_Biology_28`
- `validation_Biology_6`
- `validation_Chemistry_8`
- `validation_Chemistry_9`
- `validation_Clinical_Medicine_15`
- `validation_Clinical_Medicine_30`
- `validation_Computer_Science_8`
- `validation_Design_1`
- `validation_Design_15`
- `validation_Diagnostics_and_Laboratory_Medicine_19`
- `validation_Electronics_1`
- `validation_Energy_and_Power_19`
- `validation_Energy_and_Power_2`
- `validation_Energy_and_Power_29`
- `validation_Energy_and_Power_3`
- `validation_Finance_9`
- `validation_Geography_2`
- `validation_Geography_23`
- `validation_History_11`
- `validation_History_13`
- `validation_Marketing_14`
- `validation_Marketing_18`
- `validation_Marketing_23`
- `validation_Marketing_9`
- `validation_Materials_14`
- `validation_Materials_24`
- `validation_Materials_26`
- `validation_Math_16`
- `validation_Mechanical_Engineering_12`
- `validation_Mechanical_Engineering_16`
- `validation_Mechanical_Engineering_19`
- `validation_Mechanical_Engineering_25`
- `validation_Music_5`
- `validation_Pharmacy_1`
- `validation_Pharmacy_12`
- `validation_Pharmacy_13`
- `validation_Pharmacy_26`
- `validation_Pharmacy_4`
- `validation_Physics_10`
- `validation_Physics_13`
- `validation_Psychology_20`
- `validation_Sociology_11`
- `validation_Sociology_5`

</details>

<details>
<summary>잃은 정답 · 47개</summary>

- `validation_Accounting_1`
- `validation_Accounting_25`
- `validation_Art_21`
- `validation_Art_Theory_25`
- `validation_Basic_Medical_Science_12`
- `validation_Biology_10`
- `validation_Biology_30`
- `validation_Chemistry_2`
- `validation_Chemistry_6`
- `validation_Clinical_Medicine_11`
- `validation_Clinical_Medicine_25`
- `validation_Clinical_Medicine_5`
- `validation_Clinical_Medicine_8`
- `validation_Computer_Science_10`
- `validation_Computer_Science_14`
- `validation_Computer_Science_22`
- `validation_Computer_Science_7`
- `validation_Diagnostics_and_Laboratory_Medicine_26`
- `validation_Diagnostics_and_Laboratory_Medicine_9`
- `validation_Economics_26`
- `validation_Economics_28`
- `validation_Economics_5`
- `validation_Energy_and_Power_28`
- `validation_Finance_25`
- `validation_Geography_13`
- `validation_Geography_20`
- `validation_Geography_27`
- `validation_History_30`
- `validation_History_9`
- `validation_Manage_18`
- `validation_Marketing_13`
- `validation_Marketing_15`
- `validation_Materials_2`
- `validation_Materials_29`
- `validation_Materials_7`
- `validation_Math_25`
- `validation_Mechanical_Engineering_20`
- `validation_Mechanical_Engineering_26`
- `validation_Mechanical_Engineering_29`
- `validation_Music_16`
- `validation_Pharmacy_18`
- `validation_Pharmacy_28`
- `validation_Physics_12`
- `validation_Physics_7`
- `validation_Sociology_20`
- `validation_Sociology_23`
- `validation_Sociology_24`

</details>

<details>
<summary>계속 오답 · 366개</summary>

- `validation_Accounting_15`
- `validation_Accounting_17`
- `validation_Accounting_20`
- `validation_Accounting_21`
- `validation_Accounting_22`
- `validation_Accounting_24`
- `validation_Accounting_26`
- `validation_Accounting_28`
- `validation_Accounting_30`
- `validation_Accounting_4`
- `validation_Accounting_5`
- `validation_Accounting_6`
- `validation_Agriculture_12`
- `validation_Agriculture_13`
- `validation_Agriculture_15`
- `validation_Agriculture_17`
- `validation_Agriculture_20`
- `validation_Agriculture_21`
- `validation_Agriculture_22`
- `validation_Agriculture_27`
- `validation_Agriculture_3`
- `validation_Agriculture_4`
- `validation_Agriculture_5`
- `validation_Agriculture_8`
- `validation_Agriculture_9`
- `validation_Architecture_and_Engineering_1`
- `validation_Architecture_and_Engineering_10`
- `validation_Architecture_and_Engineering_12`
- `validation_Architecture_and_Engineering_13`
- `validation_Architecture_and_Engineering_14`
- `validation_Architecture_and_Engineering_15`
- `validation_Architecture_and_Engineering_16`
- `validation_Architecture_and_Engineering_17`
- `validation_Architecture_and_Engineering_18`
- `validation_Architecture_and_Engineering_19`
- `validation_Architecture_and_Engineering_2`
- `validation_Architecture_and_Engineering_20`
- `validation_Architecture_and_Engineering_21`
- `validation_Architecture_and_Engineering_22`
- `validation_Architecture_and_Engineering_23`
- `validation_Architecture_and_Engineering_26`
- `validation_Architecture_and_Engineering_27`
- `validation_Architecture_and_Engineering_29`
- `validation_Architecture_and_Engineering_3`
- `validation_Architecture_and_Engineering_30`
- `validation_Architecture_and_Engineering_4`
- `validation_Architecture_and_Engineering_6`
- `validation_Architecture_and_Engineering_7`
- `validation_Architecture_and_Engineering_8`
- `validation_Architecture_and_Engineering_9`
- `validation_Art_11`
- `validation_Art_12`
- `validation_Art_14`
- `validation_Art_15`
- `validation_Art_16`
- `validation_Art_18`
- `validation_Art_19`
- `validation_Art_20`
- `validation_Art_23`
- `validation_Art_26`
- `validation_Art_9`
- `validation_Art_Theory_12`
- `validation_Art_Theory_17`
- `validation_Art_Theory_3`
- `validation_Art_Theory_5`
- `validation_Basic_Medical_Science_10`
- `validation_Basic_Medical_Science_11`
- `validation_Basic_Medical_Science_14`
- `validation_Basic_Medical_Science_17`
- `validation_Basic_Medical_Science_22`
- `validation_Basic_Medical_Science_23`
- `validation_Basic_Medical_Science_25`
- `validation_Basic_Medical_Science_6`
- `validation_Biology_1`
- `validation_Biology_14`
- `validation_Biology_17`
- `validation_Biology_20`
- `validation_Biology_22`
- `validation_Biology_23`
- `validation_Biology_27`
- `validation_Biology_29`
- `validation_Biology_3`
- `validation_Biology_7`
- `validation_Biology_9`
- `validation_Chemistry_12`
- `validation_Chemistry_13`
- `validation_Chemistry_14`
- `validation_Chemistry_17`
- `validation_Chemistry_19`
- `validation_Chemistry_20`
- `validation_Chemistry_21`
- `validation_Chemistry_22`
- `validation_Chemistry_23`
- `validation_Chemistry_24`
- `validation_Chemistry_25`
- `validation_Chemistry_26`
- `validation_Chemistry_28`
- `validation_Chemistry_29`
- `validation_Chemistry_3`
- `validation_Chemistry_30`
- `validation_Chemistry_4`
- `validation_Chemistry_5`
- `validation_Chemistry_7`
- `validation_Clinical_Medicine_14`
- `validation_Clinical_Medicine_16`
- `validation_Clinical_Medicine_18`
- `validation_Clinical_Medicine_2`
- `validation_Clinical_Medicine_24`
- `validation_Clinical_Medicine_7`
- `validation_Computer_Science_1`
- `validation_Computer_Science_11`
- `validation_Computer_Science_12`
- `validation_Computer_Science_16`
- `validation_Computer_Science_18`
- `validation_Computer_Science_19`
- `validation_Computer_Science_2`
- `validation_Computer_Science_20`
- `validation_Computer_Science_23`
- `validation_Computer_Science_25`
- `validation_Computer_Science_26`
- `validation_Computer_Science_28`
- `validation_Computer_Science_4`
- `validation_Design_12`
- `validation_Design_13`
- `validation_Design_14`
- `validation_Design_2`
- `validation_Design_29`
- `validation_Design_3`
- `validation_Diagnostics_and_Laboratory_Medicine_1`
- `validation_Diagnostics_and_Laboratory_Medicine_10`
- `validation_Diagnostics_and_Laboratory_Medicine_13`
- `validation_Diagnostics_and_Laboratory_Medicine_14`
- `validation_Diagnostics_and_Laboratory_Medicine_15`
- `validation_Diagnostics_and_Laboratory_Medicine_16`
- `validation_Diagnostics_and_Laboratory_Medicine_17`
- `validation_Diagnostics_and_Laboratory_Medicine_18`
- `validation_Diagnostics_and_Laboratory_Medicine_2`
- `validation_Diagnostics_and_Laboratory_Medicine_20`
- `validation_Diagnostics_and_Laboratory_Medicine_21`
- `validation_Diagnostics_and_Laboratory_Medicine_22`
- `validation_Diagnostics_and_Laboratory_Medicine_23`
- `validation_Diagnostics_and_Laboratory_Medicine_3`
- `validation_Diagnostics_and_Laboratory_Medicine_30`
- `validation_Diagnostics_and_Laboratory_Medicine_5`
- `validation_Diagnostics_and_Laboratory_Medicine_6`
- `validation_Diagnostics_and_Laboratory_Medicine_7`
- `validation_Diagnostics_and_Laboratory_Medicine_8`
- `validation_Economics_1`
- `validation_Economics_15`
- `validation_Economics_23`
- `validation_Economics_24`
- `validation_Economics_30`
- `validation_Electronics_10`
- `validation_Electronics_11`
- `validation_Electronics_13`
- `validation_Electronics_14`
- `validation_Electronics_16`
- `validation_Electronics_17`
- `validation_Electronics_18`
- `validation_Electronics_19`
- `validation_Electronics_2`
- `validation_Electronics_21`
- `validation_Electronics_22`
- `validation_Electronics_24`
- `validation_Electronics_25`
- `validation_Electronics_26`
- `validation_Electronics_27`
- `validation_Electronics_28`
- `validation_Electronics_29`
- `validation_Electronics_30`
- `validation_Electronics_4`
- `validation_Electronics_5`
- `validation_Electronics_6`
- `validation_Electronics_7`
- `validation_Electronics_9`
- `validation_Energy_and_Power_1`
- `validation_Energy_and_Power_10`
- `validation_Energy_and_Power_12`
- `validation_Energy_and_Power_13`
- `validation_Energy_and_Power_14`
- `validation_Energy_and_Power_15`
- `validation_Energy_and_Power_16`
- `validation_Energy_and_Power_17`
- `validation_Energy_and_Power_18`
- `validation_Energy_and_Power_20`
- `validation_Energy_and_Power_21`
- `validation_Energy_and_Power_22`
- `validation_Energy_and_Power_23`
- `validation_Energy_and_Power_25`
- `validation_Energy_and_Power_26`
- `validation_Energy_and_Power_4`
- `validation_Energy_and_Power_5`
- `validation_Energy_and_Power_6`
- `validation_Energy_and_Power_7`
- `validation_Energy_and_Power_8`
- `validation_Energy_and_Power_9`
- `validation_Finance_10`
- `validation_Finance_14`
- `validation_Finance_15`
- `validation_Finance_20`
- `validation_Finance_21`
- `validation_Finance_23`
- `validation_Finance_28`
- `validation_Finance_29`
- `validation_Finance_30`
- `validation_Finance_5`
- `validation_Finance_8`
- `validation_Geography_1`
- `validation_Geography_10`
- `validation_Geography_11`
- `validation_Geography_14`
- `validation_Geography_17`
- `validation_Geography_24`
- `validation_Geography_30`
- `validation_Geography_4`
- `validation_Geography_5`
- `validation_Geography_6`
- `validation_Geography_7`
- `validation_Geography_8`
- `validation_Geography_9`
- `validation_History_10`
- `validation_History_2`
- `validation_History_23`
- `validation_History_5`
- `validation_History_6`
- `validation_History_7`
- `validation_History_8`
- `validation_Literature_14`
- `validation_Literature_18`
- `validation_Literature_21`
- `validation_Literature_24`
- `validation_Literature_26`
- `validation_Literature_28`
- `validation_Manage_12`
- `validation_Manage_13`
- `validation_Manage_19`
- `validation_Manage_20`
- `validation_Manage_22`
- `validation_Manage_23`
- `validation_Manage_24`
- `validation_Manage_26`
- `validation_Manage_27`
- `validation_Manage_3`
- `validation_Manage_4`
- `validation_Manage_6`
- `validation_Manage_7`
- `validation_Marketing_12`
- `validation_Marketing_28`
- `validation_Marketing_4`
- `validation_Marketing_8`
- `validation_Materials_1`
- `validation_Materials_10`
- `validation_Materials_11`
- `validation_Materials_12`
- `validation_Materials_13`
- `validation_Materials_16`
- `validation_Materials_17`
- `validation_Materials_18`
- `validation_Materials_19`
- `validation_Materials_20`
- `validation_Materials_21`
- `validation_Materials_22`
- `validation_Materials_25`
- `validation_Materials_27`
- `validation_Materials_28`
- `validation_Materials_3`
- `validation_Materials_30`
- `validation_Materials_4`
- `validation_Materials_6`
- `validation_Materials_9`
- `validation_Math_12`
- `validation_Math_13`
- `validation_Math_15`
- `validation_Math_17`
- `validation_Math_19`
- `validation_Math_2`
- `validation_Math_20`
- `validation_Math_22`
- `validation_Math_26`
- `validation_Math_28`
- `validation_Math_3`
- `validation_Math_4`
- `validation_Math_5`
- `validation_Math_8`
- `validation_Math_9`
- `validation_Mechanical_Engineering_1`
- `validation_Mechanical_Engineering_10`
- `validation_Mechanical_Engineering_11`
- `validation_Mechanical_Engineering_13`
- `validation_Mechanical_Engineering_14`
- `validation_Mechanical_Engineering_15`
- `validation_Mechanical_Engineering_17`
- `validation_Mechanical_Engineering_18`
- `validation_Mechanical_Engineering_2`
- `validation_Mechanical_Engineering_21`
- `validation_Mechanical_Engineering_22`
- `validation_Mechanical_Engineering_23`
- `validation_Mechanical_Engineering_27`
- `validation_Mechanical_Engineering_28`
- `validation_Mechanical_Engineering_3`
- `validation_Mechanical_Engineering_30`
- `validation_Mechanical_Engineering_4`
- `validation_Mechanical_Engineering_5`
- `validation_Mechanical_Engineering_7`
- `validation_Mechanical_Engineering_8`
- `validation_Mechanical_Engineering_9`
- `validation_Music_1`
- `validation_Music_11`
- `validation_Music_13`
- `validation_Music_14`
- `validation_Music_15`
- `validation_Music_17`
- `validation_Music_18`
- `validation_Music_19`
- `validation_Music_2`
- `validation_Music_20`
- `validation_Music_21`
- `validation_Music_22`
- `validation_Music_23`
- `validation_Music_24`
- `validation_Music_25`
- `validation_Music_27`
- `validation_Music_28`
- `validation_Music_29`
- `validation_Music_3`
- `validation_Music_30`
- `validation_Music_4`
- `validation_Music_6`
- `validation_Music_7`
- `validation_Music_8`
- `validation_Music_9`
- `validation_Pharmacy_17`
- `validation_Pharmacy_19`
- `validation_Pharmacy_20`
- `validation_Pharmacy_21`
- `validation_Pharmacy_23`
- `validation_Pharmacy_27`
- `validation_Pharmacy_30`
- `validation_Physics_1`
- `validation_Physics_15`
- `validation_Physics_18`
- `validation_Physics_19`
- `validation_Physics_2`
- `validation_Physics_20`
- `validation_Physics_9`
- `validation_Psychology_12`
- `validation_Psychology_24`
- `validation_Psychology_26`
- `validation_Psychology_30`
- `validation_Psychology_6`
- `validation_Psychology_9`
- `validation_Public_Health_1`
- `validation_Public_Health_11`
- `validation_Public_Health_24`
- `validation_Public_Health_28`
- `validation_Public_Health_30`
- `validation_Public_Health_9`
- `validation_Sociology_1`
- `validation_Sociology_10`
- `validation_Sociology_12`
- `validation_Sociology_15`
- `validation_Sociology_21`
- `validation_Sociology_25`
- `validation_Sociology_27`
- `validation_Sociology_3`
- `validation_Sociology_9`

</details>

## 실제 실행 코드와 보존 범위

- `evaluate.py`: 처음 실행한 코드. 원본888개에서135분 제한으로 종료됐다. SHA256 `bd8ff39a7dbbdb33755107a243960b27507ed9d20849052903a667c4eaae2d50`.
- `evaluate_resume.py`: 검증된888개를 복원하고 원본 마지막12개 + SFT900개를 평가한 실제 재개 코드. SHA256 `3f18a9801595fa32678096a1de8985c46bcece5b7f8dfa543badbb09d96612a8`. 원본 남은 창 제한30분, SFT 제한4시간, 전체5시간과 백업 확인 제한10분. 생성·채점 조건은 동일하다.
- `reproduce.py`: 이전 고정 코어를 가리키는 상대 심볼릭 링크. 코어를 바꾸지 않았다.
- [고정된 자체 합성48개 묶음](../finish_sft_20261118/frozen_bundle.zip), [결정적 학습 코드/노트북](../finish_sft_deterministic_20261118/README.md), [체크포인트 복구 도구](../finish_sft_20261118/recover_checkpoint.py).
- 중단 전 코드와 재개 코드를 모두 보존하기 위해 이번 공개 변경은5개 파일이다. 학습·평가에 새 의존성이나 새로운 학습 방법을 추가하지 않았다.
- 실제 실행 notebook에는 가중치와 복원용 원본 응답이 내장돼 있어 비공개 본인Drive에 보존했다. 공개 저장소에는 공식 MMMU 질문·보기·정답·그림/응답 원문/가중치 파일을 넣지 않았다. 위 `colab/results/...`의 상세 근거 파일은 로컬·개인 백업 경로다.

### 다시 확인하는 순서

1. 고정된 이전 자료 묶음과 결정적 학습 노트북으로48개를 학습한다. 실제 선택 정책은 `strict_auto`이며 두 독립 학습의144개 텐서와 어댑터 SHA256이 이 문서의 값과 같은지 확인한다. 다른 수치 정책/버전에서 다른 가중치가 나오면 이 가중치의 재현이라고 표시하지 않는다.
2. 원본 모델·MMMU·평가 코드의 고정 revision을 유지한다. `prepare`에서 실제 어댑터144개와 병합 가중치 SHA가 일치해야 다음으로 넘어간다. `infer`는900개 실제 입력/엔진 prompt token SHA/문항 seed를 잠금 자료와 대조한다.
3. 이번 실제 경로의 재구성은 초기8개 + 재개11개 =19개 증분ZIP과ready marker를 순서대로 검증한다. 초기 실행의 마지막 서버 확인8은 별도 보존한 출력 기록도 함께 사용한다. 마지막ZIP 하나로 전체 결과를 복구할 수 없다.
4. 깨끗한 새900 전체 재실행과 이번 부분 재개를 구별한다. 초기 코드의135분 제한은 백업 확인 대기를 포함하므로 이 환경에서 부족했다. 이 기록을 그대로 재구성하는 재개 코드는 원본888개 백업을 요구한다. 새 실험에서 시간 제한을 바꾼다면 새 소스 해시와 실행 조건을 기록해야 한다.
5. 각 조건900개 고유ID/실제 입력·시드/누락·중복·오류를 검사하고, 저장 원문을 동일한 고정V8로 독립 재채점한다. 전체1800개와 원격 비교의 일치 및 모든 백업 왕복 검증을 통과한 값만 최종 결과로 사용한다.

### 백업 검증 기록

| 순서 | 단계 | bytes | SHA256 |
|---:|---|---:|---|
| 1 | prepared | 13,772 | `518c266d9075b3f808b07573584eb7ff6f622442049f12f0d3c5cee21ffd4ba6` |
| 2 | base_006 | 350,207 | `900b03ba486a5a18a4ac27667b8b35fe00324f549dbd8731c6b21fc66e5e4660` |
| 3 | base_012 | 391,443 | `eeb5de2271883acada31a3a888fb6169da0c75409edb99f106164008225e8b56` |
| 4 | base_018 | 370,798 | `c8e98a77202160fb40699a5ed5f5c119f9ef5a9c8bd0fd1840e20a6897cf9770` |
| 5 | base_024 | 373,052 | `7d66b9022ae279cf70035ff13dc75fbdc91f917e41bc8a760c0479c055b4cd9d` |
| 6 | base_030 | 526,231 | `bfdf0ecda4540a3bbc8aa3cf0b44f491e53f58b9c3a98b0821fe7db8ac3d52ba` |
| 7 | base_036 | 402,403 | `4ea35cc3f22905d9cccfa13361eba32dc2b76b0c0dac520ee5cc0c91c5648279` |
| 8 | final | 47,838 | `554f6f1ba64e299cb2cd37228e7e025401fb61368f70a241d1876a75bc1cb55d` |
| 9 | prepared | 17,266 | `fc4873bfc7cd4413d11a1b20724162f20fae4b4b8c0866629a9006baaccda84f` |
| 10 | base_038 | 23,256 | `89bc7cbbfa1723290d8bdb7237b00e8ad9445a3cc39da58ba07b8a869937e85e` |
| 11 | sft_006 | 340,703 | `3d0b712c636bbe5acee27c1358d6061cd987ab0c019369c2fe186e5d8d0a6988` |
| 12 | sft_012 | 341,515 | `21874176eeb66c8dd80fc9432b77faec6ca5c3da5a705a896145ddfd1c8ddc0b` |
| 13 | sft_018 | 335,967 | `2a513abe8b82ef17bebdc02b97a04babbf5607684b97c64fe88abca5e49bdba0` |
| 14 | sft_024 | 351,389 | `8ed8969dd6ed92b0a46b4679fab7f48b5aab73676c7c6d1942d29c286c0ebc52` |
| 15 | sft_030 | 480,191 | `62e0b49c207eea23f661800070d6909d062483032d904cd90facee807faa98fe` |
| 16 | sft_036 | 355,120 | `7c9c0327a3998ec994bbe1ae07aca8ec195d93d20b7ae5baf272dd43b5c3ef79` |
| 17 | sft_038 | 63,787 | `0da43b9722d274f3f00fb46459e814a38c7cba147cfa1d82ed7abe79ad9dedee` |
| 18 | comparison | 5,634 | `2452486b2503162f60e83ca5484a44ba9544198220f2a530fa5b6de2dcef09d0` |
| 19 | final | 1,428 | `5bf370dc00decfe9136c51b2dd44994346e80b2a379c4df5954ba62291af5e22` |

19개 모두 실제 Drive 회수 바이트·전체SHA256·ZIP CRC·내부 모든 파일 해시와ready marker 바이트를 검사했다. 원격 원본/LoRA1800개 재채점 결과와 로컬 고정V8의 모든 채점 필드가 일치했다. HTML의 브라우저 시각 검증은 기존 로컬 파일 접근 제한으로 미완료이며 이를 우회하지 않았다.

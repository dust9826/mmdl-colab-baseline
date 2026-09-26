# MMMU · L4 실행 및 별도 재채점

개인 진행 공유용 저장소입니다. **900문항 전체 실행은 아직 시작하지 않았습니다.**
목표는 원문 응답을 한 번 확보한 뒤, GPU를 다시 사용하지 않고 채점·분석하는 것입니다.

## 출처와 역할

평가 엔진은 [jang2296/MMDL](https://github.com/jang2296/MMDL)의
`f1235cf76f1c5637ea61b72a7d36b01c8fbc73a1` 커밋을 그대로 사용합니다.
프롬프트·V8 파서·데이터 취득·기록 형식은 해당 팀원 구현이며, 우리가 새로 만든 것으로 주장하지 않습니다.
이 저장소는 Colab 실행, Drive 백업/복원, 실행 후 별도 재채점 절차를 제공합니다.
원본 저장소는 공개 URL에서 정확한 커밋으로 clone하므로 이 비공개 저장소의 인증 정보를 Colab에 입력할 필요가 없습니다.

## 진행 계획과 완료 기준

1. **준비:** 이 저장소와 노트북 버전을 고정하고 L4를 선택합니다. 기본 파서는 `team-final-answer-v8`입니다.
2. **원문 확보:** 900문항을 같은 설정으로 실행합니다. 초반 결과·메모리·속도를 관찰하고 매 문항 Drive에 백업합니다.
3. **완전성 확인:** 30과목 각각 30개, 총 900개의 고유 문항, 시스템 오류·누락 없음, 기록 hash 일치를 검사합니다.
4. **독립 채점:** 원문을 변경하지 않고 `rescores/`에 새 점수와 파서 버전을 저장합니다.
5. **분석·제출:** 오류/응답 잘림/추출 실패 사례를 확인하고 30과목 표, 종합 macro average, 공식 67.4와의 차이 분석을 작성합니다.
   제출용 `reports/mmmu_baseline.md`는 실제 실행 결과를 확보한 뒤 공식 템플릿으로 작성합니다.

## Colab 실행

1. [colab/L4_MMMU.ipynb](colab/L4_MMMU.ipynb)를 내려받아 Colab의 파일 → 노트북 업로드로 엽니다.
2. L4 런타임을 선택하고 위에서부터 환경 준비·Drive 복원 셀을 실행합니다.
3. 새로운 전체 실행의 JOB_ID 기본값은 `mmmu-l4-full-01`입니다. 기존 테스트 폴더와 분리됩니다.
4. 실제 리소스 화면의 CU 잔액/시간당 요율을 확인합니다.
5. 전체 실행 셀의 `RUN_FULL=True`, `AUTO_DISCONNECT=True`로 설정하고 해당 셀부터 마지막 셀까지 실행합니다.
   마지막 셀은 완전성 검사 → 별도 V8 재채점 → 재채점 검사 → Drive 최종 백업 → 런타임 해제를 수행합니다.
6. 오류가 나면 자동 종료 단계에 도달하지 않을 수 있습니다. 백업 메시지를 확인하고 필요하면 수동으로 런타임을 삭제합니다.

긴 실행은 한 세션에서 이어갑니다. 예기치 않은 종료 시 같은 JOB_ID로 다시 실행하면 완료 기록을 복원합니다.
**GPU·드라이버·Python·패키지·adapter가 다르면 재개가 차단됩니다.** Colab 재배정 시 이 조건이 맞는다는 보장은 없습니다.
동일 JOB_ID로 두 노트북을 동시에 실행하지 마세요. 런타임 삭제 전 최종 백업을 확인하세요.

## 추론과 채점의 분리

상류 엔진은 추론하면서 기존 V8 점수도 함께 기록합니다. 이것을 제거하기 위해 엔진을 변경하지 않습니다.
보존된 `raw_response`를 읽는 별도 재채점 명령이 있으므로, 최종 채점은 추론과 독립적으로 반복할 수 있습니다.
추론 단계에는 GPU가 필요하지만 재채점 계산에는 GPU가 필요하지 않습니다.

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

## 현재 확인한 범위

2026-09-26 기존 노트북으로 A100과 L4 각각 같은 회계 3문항을 완료했습니다. 둘 다 3/3 정답이며 전체 성적은 아닙니다.
평가 구간 A100 39.37초, L4 45.65초. 당시 UI 요율 5.30/1.54CU/시간. 요율은 현재 리소스 화면에서 재확인합니다.
두 테스트의 Drive 백업·런타임 종료를 확인했습니다. 긴 응답과 900문항 전체 안정성은 아직 미검증입니다.
이 저장소에 추가한 실행 후 재채점·자동 종료 연결은 실제 GPU에서 아직 실행하지 않았습니다.

[과제 안내](https://gist.github.com/neur-lab/38deabdfcde9e6dbacf362ab8059eb41) ·
[제출 템플릿](https://gist.github.com/neur-lab/483852e1f9d8d52f54627e600677c2f9)

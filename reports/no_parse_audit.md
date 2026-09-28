# L4 MMMU — NO_PARSE 87문항 사후 검토

작성일: 2026-09-28 · 실행: `mmmu-l4-full-01-evaluation`

**87개를 모두 같은 기준으로 검토한 결과, 최종 답이 정답과 일치하는데 V8에서 점수를 받지 못한 사례 7개를 확인했다.** 명확한 오답은 4개이며 나머지 76개는 답이 불명확하거나 기준 정답의 허용 범위가 애매해 판정을 유보했다.
**기존 V8 점수 564/900 = 62.67%는 유지한다.** 이 문서는 보존된 응답을 해석한 추가 분석이며, 수정한 파서로 전체 900개를 재채점한 새 성적이 아니다.

[전체 실험 보고서](mmmu_baseline.md) · [87문항 검토 데이터](../results/l4-full-20260928/no_parse_audit.json)

## 검토 방법과 범위

1. 최종 V8 결과에서 `NO_PARSE`인 **87개 고유 문항만** 선정했다. 정상 종료(`stop`) 21개, 출력 상한 종료(`length`) 66개다.
2. 판정 기준을 먼저 정하고, 1차 검토에는 정답·정오 정보를 제외한 문제·보기·응답 자료를 사용했다. 세 묶음 29개씩 검토한 후 주 검토자가 통합했다.
3. 단일한 최종 답이 확정됐는지 먼저 판단했다. 명시적인 자기 정정은 인정하되, 미해결 답안 충돌·추측·보기 번호와 보기 내용의 불일치·답변 미완결은 유보했다. 답을 새로 풀거나 정답에 맞는 중간 문장만 선택하지 않았다.
4. 명확한 답으로 판정한 경우에만 기준 정답과 비교했다. 분수·제곱근의 명백한 동치는 해석하되, 위치 번호·cis/trans 같은 의미를 바꾸는 정보는 지우지 않았다.
5. 인용 근거가 실제 원문에 존재하는지 확인하고 원문 내 문자 위치·SHA-256을 기록했다. 원본 응답과 원본 채점 파일은 수정하지 않았다.

**검토 주체는 AI 어시스턴트이며 사람 전문가의 독립 검수는 아니다.** 원문은 약 716만 자다. 87개 모두의 응답 시작·마지막 6,000자·중복을 합친 답안 선언 문단을 확인하고, 명확한 답과 정정·충돌 경계 사례는 원문 전체 또는 해당 문맥을 추가 검토했다. 긴 반복 응답 87개 전문의 모든 문장을 사람이 정독했다고 주장하지 않는다. 선언 문단 추출은 탐색 보조이며 응답 전체 의미를 완벽히 보장하지 않는다.

이미지 자체의 정답성을 다시 심사하거나 813개 `PARSED` 문항을 수작업으로 재검토하지 않았다. 따라서 아래 7개는 **이번 검토 기준으로 확인한 사례 수**이며, 전체 채점 오류의 총수나 사람 기준 실제 정확도는 아니다.

## 결과

| 구분 | 정상 종료 | 출력 상한 종료 | 합계 |
|---|---:|---:|---:|
| 최종 답이 정답과 일치하지만 V8는 오답 | 7 | 0 | **7** |
| 명확한 최종 답이 정답과 다름 | 4 | 0 | **4** |
| 최종 답 불명확·미완결 | 9 | 66 | 75 |
| 기준 정답의 지명 범위·별칭이 애매함 | 1 | 0 | 1 |
| 전체 | **21** | **66** | **87** |

정답과의 비교를 유보한 76개를 정답이나 확정 오답으로 재분류하지 않았다. 상한 종료 66개에서 이번 기준으로 명확한 정답을 확인하지 못했다는 사실은, 상한 종료가 원래 항상 오답이라는 뜻이 아니다. 전체 900개에는 별도로 **V8가 정답으로 채점한 상한 종료 10개**가 있다.

## 정답 누락을 확인한 7개

| 문항 | 응답의 최종 답 | 기준 정답 | V8 실패 이유 | 해석 |
|---|---|---|---|---|
| Math 15 | `24/7 ft/sec` | `24/7`, `3.429` | `multiple_numeric_values` | 분수·상자·단위 표기를 처리하는 경로에서 24와 7을 별개 숫자로 취급 |
| Electronics 2 | `2√2 A` ≈ 2.828427 A | `2.83` | `multiple_numeric_values` | 제곱근 계수와 피제곱근을 여러 숫자로 읽음. 소수 둘째 자리로 같은 값 |
| Electronics 13 | 수식 상자 안의 `C`와 해당 식 | `C` | `unsupported_mcq_expression` | 중첩된 수식·상자 표기 안의 보기 C를 추출하지 못함 |
| Chemistry 2 | 앞선 A를 부정·정정한 후 `Final Answer: B` | `B` | `conflicting_declarations` | 명시적 자기 정정이 있으나 이전 답과 충돌로 처리 |
| Chemistry 30 | 일반식 `MS`에서 M=Mg를 특정해 `MgS` | `MgS` | `conflicting_or_invalid_boxes` | 일반식을 구체화한 결과를 서로 다른 상자 답의 충돌로 처리 |
| Materials 10 | 초기 D를 명시적으로 정정한 후 `A` | `A` | `conflicting_declarations` | 정정 이후 결론을 이전 선언과 충돌로 처리 |
| Pharmacy 12 | 초기 B를 틀렸다고 명시하고 최종 `A. True` | `A` | `conflicting_declarations` | 반복 검토가 있으나 마지막의 명시적 정정·최종 선택을 반영하지 못함 |

앞의 **3개는 표기·수식 처리 한계**, 뒤의 **4개는 자기 정정·구체화를 어떻게 인정하느냐의 차이**다. 후자의 모든 응답을 단순히 파서 버그라고 부르기보다는, 현재의 보수적인 충돌 처리 규칙과 문맥을 읽는 사후 판단이 달랐다고 구분한다.

7문항은 전체 900문항의 **0.78%p**에 해당한다. 이 규모만으로 공식 비교값과의 **4.73%p 격차 전체**를 설명할 수 없다. 새로운 정확도 수치로 대체하지 않으며, 실제 영향은 수정한 일반 규칙을 전체 900개에 동일 적용해 정답→오답 변화도 함께 확인해야 한다.

## 추출 실패가 곧 놓친 정답은 아닌 사례

| 문항 | 해석 가능한 최종 답 | 기준 정답 | 판단 |
|---|---|---|---|
| Biology 27 | `B. Aa` | `E` | 실제 B 보기와 내용은 일치하지만 기준 정답과 다름 |
| Chemistry 4 | `cis-1-chloro-2-methylcyclohexane` | `trans-1-Chloro-4-methylcyclohexane` | 입체·위치 정보가 달라 오답 |
| Electronics 26 | `11 μF` | `6.333` | 최종 수치가 다름 |
| Electronics 30 | `−106.26°` | `−141` | 최종 수치가 다름 |

**Physics 2**는 최종 답을 `A. To the right / To the left`라고 썼지만 실제 A 보기는 `To the right / To the right`, B 보기가 `To the right / To the left`다. 정답에 맞는 쪽만 골라 번호나 내용을 우선할 수 없어 유보했다.

**Geography 4**는 `Clearwater, Florida`라고 답했는데 기준에는 `Tampa`와 `Florida`가 함께 있다. 도시가 다르지만 넓은 지역 별칭이 겹치므로, 지명 범위에 대한 사전 규칙 없이 점수를 인정하거나 확정 오답으로 판단하지 않았다.

**Accounting 15·17** 등은 계산·후보 답을 반복하다 상한에서 종료했다. 정답 문자열이 중간에 등장하는 것만으로 최종 답이 확정됐다고 간주하지 않았다.

## 과제 분석에 반영할 결론

이번 baseline은 모델의 답 생성 능력과 V8의 답 추출 규칙이 함께 반영된 측정값이다. 표기 처리와 자기 정정 해석 때문에 놓친 정답을 7개 확인했으므로, `NO_PARSE`를 전부 모델의 지식 부족으로 설명하면 안 된다. 동시에 87개를 모두 채점 오류로 설명할 수도 없다. 보존된 응답에는 명확한 오답과 반복·모순·미완결 답변도 존재한다.

지금은 원본 baseline을 보존하고 이 진단을 보고서에 추가한다. 이후 파서를 개선한다면 문항 ID·정답별 예외가 없는 새 버전으로 만들고, 정정·충돌·수식·단위에 대한 양성/음성 사례를 검증한 뒤 전체 900개에 동일 적용해야 한다. 파서 변경으로 비교 기준이 바뀌므로, fine-tuning 전후 결과도 같은 버전으로 다시 채점해야 한다. **이 후속 작업에는 저장된 응답을 사용하므로 GPU 재추론이 필요 없다.**

## 문항별 검토 기록 — 87개

아래 표의 ‘판정 유보’는 이번 추가 분석의 판정이다. 원래 V8 점수에서는 모두 오답 처리된 상태를 유지한다. `stop`은 모델 생성의 정상 종료, `length`는 32,768토큰 상한 종료를 뜻한다.

| 문항 ID | 종료 | 기존 추출 실패 사유 | 검토 결과 | 원문 해석·판정 근거 |
|---|---|---|---|---|
| `Accounting_15` | `length` | `no_asserted_declaration` | 판정 유보 | $5,040/C를 여러 차례 제안하지만 계속 perhaps로 추정하고 계산을 부정하며, 응답이 미완성으로 끝나 확정된 최종 답이 없다. |
| `Accounting_17` | `length` | `unsupported_mcq_expression` | 판정 유보 | 응답은 total assets의 의미와 계산법을 계속 추측하며 끝에 “perhaps”로 문장이 끊겼습니다. 확정 답이 없습니다. |
| `Accounting_21` | `length` | `unsupported_mcq_expression` | 판정 유보 | 응답은 선택지를 확정하지 않은 채 평균 자본비용 해석을 여러 번 ‘Perhaps’로 반복하고, 마지막에는 X를 거부하자는 미완성 계산으로 끝난다. 앞서 ‘no incorrect decisions’라고 했다가 D를 틀렸다고 해석하는 등 결론도 안정되지 않았다. |
| `Accounting_22` | `length` | `unsupported_mcq_expression` | 판정 유보 | 계산과 가정만 이어지고 결론이나 최종 선택을 선언하기 전에 응답이 중단된다. |
| `Accounting_5` | `length` | `no_asserted_declaration` | 판정 유보 | 마지막까지 어떤 연도/기간의 equivalent units를 묻는지 추측하고 값들을 배제하는 중이며, 끝은 숫자 “2”에서 잘렸습니다. 최종 선택이 없습니다. |
| `Architecture_and_Engineering_10` | `length` | `unsupported_mcq_expression` | 판정 유보 | 계산 방법과 면적 값이 맞지 않는다고 되풀이하며, 특정 선택지나 최종 결과를 확정하지 않는다. 응답은 D.M.D. 값을 나열하는 도중 길이 종료됐다. |
| `Architecture_and_Engineering_12` | `length` | `no_asserted_declaration` | 판정 유보 | 서로 다른 방위 값을 option A라고 여러 차례 tentative하게 지목하며 어느 값도 명시적으로 확정하거나 앞선 추정을 정정하지 않는다. |
| `Architecture_and_Engineering_13` | `length` | `no_asserted_declaration` | 판정 유보 | 5.66 mm와 4.22 mm를 모두 “perhaps”로 제안했고, 최종에도 계산이 맞는지 확정하지 못한 채 답변이 끝났습니다. |
| `Architecture_and_Engineering_14` | `length` | `no_explicit_final` | 판정 유보 | 끝부분까지 여러 가정을 제안할 뿐 값이나 선택지를 최종 답으로 확정하지 않는다. 마지막 문장도 필요한 관성모멘트가 없다는 가정 검토 도중 끝난다. |
| `Architecture_and_Engineering_15` | `length` | `no_asserted_declaration` | 판정 유보 | -1.84 kips를 반복해 perhaps로 제시하지만, 계산상 다른 결과를 계속 내고 마지막도 가설 전개 중 끊겨 답이 확정되지 않는다. |
| `Architecture_and_Engineering_18` | `length` | `no_asserted_declaration` | 판정 유보 | 945.8 m, 216°45′를 반복해서 “perhaps”로만 제시하고, 이어 계산 오류 가능성을 언급하며 마지막 문장도 미완성입니다. |
| `Architecture_and_Engineering_29` | `length` | `unsupported_mcq_expression` | 판정 유보 | 수평거리 공식에 대해 맞지 않는다고 반복해서 번복하며 특정 결과를 최종 선택하지 않는다. 종료부도 공식을 다시 쓰는 중 잘려 있다. |
| `Architecture_and_Engineering_9` | `length` | `no_asserted_declaration` | 판정 유보 | 14,500과 9,446 등 상충 수치를 반복 추정하고, 마지막에는 가장 가까운 답을 고르겠다고만 하며 선택을 완료하지 않는다. |
| `Art_Theory_5` | `length` | `article_a` | 판정 유보 | 응답 안에서 C를 “Final Answer”로 선언한 뒤 A로 바꾸지만, A도 “wrong”이라고 말하고 마지막에는 “But I recall now: Stone”에서 잘립니다. 명시적 정정으로 해소된 최종 결론이 없습니다. |
| `Biology_27` | `stop` | `label_option_conflict` | 명확한 오답 | 마지막 genotype 판단과 명시적 Final Answer가 모두 B. Aa로 일치한다. 최종 해석 `B. Aa`, 기준 정답 `E`. |
| `Chemistry_14` | `length` | `unsupported_mcq_expression` | 판정 유보 | 3이라고 결론짓겠다고 했다가 옵션 때문에 A.4를 고르겠다고 하고 다시 3과 4를 오간다. 최종 꼬리에서도 A.4는 추측형이며 답이 확정되지 않는다. |
| `Chemistry_19` | `stop` | `conflicting_declarations` | 판정 유보 | 4와 2를 오가며 끝에는 2를 “final answer”로 적었지만, 앞선 4 결론을 명시적으로 철회했다고 보기 어렵고 여러 차례 상반된 최종 선언이 남습니다. |
| `Chemistry_2` | `stop` | `conflicting_declarations` | 정답 누락 확인 | 중간에 A를 정답이라고 했으나, 이후 해당 판단을 다시 검토하고 B를 best answer라고 명시한 뒤 마지막 Final Answer에서도 B를 확정한다. 최종 해석 `B`, 기준 정답 `B`. |
| `Chemistry_30` | `stop` | `conflicting_or_invalid_boxes` | 정답 누락 확인 | 처음에는 일반식 MS를 상자에 넣었지만, 뒤에서 M이 Mg임을 명시하고 화합물을 MgS로 확정해 일반식을 구체화했다. 최종 해석 `MgS`, 기준 정답 `['$MgS$', 'MgS']`. |
| `Chemistry_4` | `stop` | `multiple_numeric_values` | 명확한 오답 | 마지막에 동일한 분자명을 답으로 반복해 확정합니다. 최종 해석 `cis-1-chloro-2-methylcyclohexane`, 기준 정답 `trans-1-Chloro-4-methylcyclohexane`. |
| `Clinical_Medicine_15` | `length` | `unsupported_mcq_expression` | 판정 유보 | 정상 영상이라 선택지 없음이라는 판단과 A 또는 D를 고르자는 추측이 계속 교차한다. 끝에서도 ‘none of the…’로 잘려 유일하게 확정된 선택지가 없다. |
| `Computer_Science_1` | `stop` | `conflicting_declarations` | 판정 유보 | 앞부분에서 E가 의도된 답이라고 여러 번 제시한 뒤 D라고 바꾸지만, E를 명시적으로 철회하는 정정 없이 서로 다른 최종 후보가 남는다. |
| `Computer_Science_11` | `length` | `multiple_choice_alternatives` | 판정 유보 | A,B,D가 가능하다고 하면서 단일 선택 문제라고 A를 박스 처리했지만, 곧바로 C일 수도 있다고 하고 “that would be wrong”에서 끊깁니다. 최종 선택이 안정적으로 확정되지 않았습니다. |
| `Electronics_1` | `length` | `unsupported_mcq_expression` | 판정 유보 | 회로 상태를 분석하던 중 기초 가정을 번복하고, 마지막에는 전류 식의 V 항을 쓰다 끝난다. 포화 여부를 최종 답으로 선언하지 않았다. |
| `Electronics_10` | `stop` | `conflicting_declarations` | 판정 유보 | D를 여러 차례 고르지만 근거 문맥에서 perhaps로 계속 의심하고 값이 옵션과 맞지 않는다는 상충이 해소되지 않는다. 최종 표기만으로는 정책상 모호성이 해소되지 않는다. |
| `Electronics_11` | `length` | `no_explicit_final` | 판정 유보 | 응답은 노드 전류 방정식을 세우는 중간에 “So”에서 끊겼습니다. 최종 물리량이나 답은 제시되지 않았습니다. |
| `Electronics_13` | `stop` | `unsupported_mcq_expression` | 정답 누락 확인 | 주기함수 라플라스 변환 유도를 마친 뒤 Final Answer에서 C와 공식을 함께 제시한다. 최종 해석 `C`, 기준 정답 `C`. |
| `Electronics_17` | `length` | `unsupported_mcq_expression` | 판정 유보 | 가능한 회로 해석과 값을 추측할 뿐 답 선택이나 최종 답 선언 없이 문장 중간에서 끝난다. |
| `Electronics_2` | `stop` | `multiple_numeric_values` | 정답 누락 확인 | 최종 답 섹션과 마지막 문장에서 같은 RMS 값을 확정적으로 제시합니다. 최종 해석 `2√2 A`, 기준 정답 `2.83`. |
| `Electronics_26` | `stop` | `conflicting_declarations` | 명확한 오답 | 여러 차례 해석을 검토하지만, 마지막에 11 μF를 선택하고 boxed Final Answer로 확정한다. 최종 해석 `11 μF`, 기준 정답 `6.333`. |
| `Electronics_28` | `length` | `no_asserted_declaration` | 판정 유보 | A를 수차례 perhaps라고 제안하며 120V, 75V 등 서로 맞지 않는 주장과 함께 반복한다. 꼬리에도 잠정 문장만 반복되고 확정된 최종 답이 없다. |
| `Electronics_30` | `stop` | `conflicting_declarations` | 명확한 오답 | 위상값을 여러 번 동일하게 선언하고, 최종 표기의 단위 생략은 바로 앞 문맥에서 phase로 특정되어 값이 분명합니다. 최종 해석 `−106.26°`, 기준 정답 `-141`. |
| `Electronics_6` | `length` | `multiple_numeric_values` | 판정 유보 | 회로를 직렬·병렬로 해석하는 여러 시도를 하다가 마지막에 분기 하나를 쓰는 도중 끝난다. 최종 수치나 선택지를 확정하지 않는다. |
| `Electronics_7` | `stop` | `no_asserted_declaration` | 판정 유보 | 앞서 A, B, C를 서로 다른 위상·진폭으로 추정하고 C를 고른다고 반복하지만, 근거에서도 가장 가깝다는 식으로 잠정 선택한다. 마지막 C 상자는 이를 해결하는 명시적 정정이 아니다. |
| `Energy_and_Power_1` | `length` | `no_asserted_declaration` | 판정 유보 | 반구 열전달식과 반경 단위를 계속 재검토하지만 마지막은 “Let me try” 계산 시작에서 끊깁니다. 답을 확정하지 않았습니다. |
| `Energy_and_Power_12` | `length` | `no_asserted_declaration` | 판정 유보 | 210이라는 수를 반복 언급하지만 매번 ‘Perhaps’로 제시하고 선택지에 없다고 덧붙인다. 다른 공식·단위 해석을 검토하며 확정하지 않는다. |
| `Energy_and_Power_13` | `length` | `no_asserted_declaration` | 판정 유보 | 품질 값을 정하는 데 필요한 미지수가 남았다고 설명하다가 계산 중간에서 끝나며, 최종 값이나 선택을 선언하지 않는다. |
| `Energy_and_Power_14` | `length` | `no_asserted_declaration` | 판정 유보 | 끝부분은 h의 의미를 1 m 또는 0.5 m라고 추측하고 “not matching”이라며 끝나며, 앞에서도 0.5 m를 tentative로 제시합니다. 확정 답이 아닙니다. |
| `Energy_and_Power_15` | `length` | `unsupported_mcq_expression` | 판정 유보 | 에너지 방정식이 순환적이거나 불가능하다고 검토하고 다른 접근을 찾는 중 끝난다. 최종 답이 없다. |
| `Energy_and_Power_17` | `length` | `unsupported_mcq_expression` | 판정 유보 | 100m라고 주장하면서 50m를 선택할 수도 있다고 말하고, 100m도 50m도 확정된 최종 선택으로 일관되게 유지하지 않는다. |
| `Energy_and_Power_20` | `length` | `unsupported_mcq_expression` | 판정 유보 | 압력 해석을 여러 가능성으로 추측하다가 “Perhaps”로 끝났고, 계산 결과나 답을 확정하지 않았습니다. |
| `Energy_and_Power_22` | `length` | `no_asserted_declaration` | 판정 유보 | 818 kPa와 약 232 kPa처럼 서로 다른 계산 결과를 서로 다른 추정 조건으로 제시하면서 어떤 것을 답으로 확정하지 않는다. 마지막 부분도 높이 해석을 계속 추측한다. |
| `Energy_and_Power_26` | `length` | `unsupported_mcq_expression` | 판정 유보 | 계산으로 약 3900을 얻었다고 한 뒤 3400과 3600 중 어느 쪽인지 tentative하게 오가지만 최종 선택은 없다. |
| `Energy_and_Power_4` | `length` | `unsupported_mcq_expression` | 판정 유보 | 0.1769, 옵션 C의 0.00247, 옵션 A의 0.00147 등을 tentative로 번갈아 제시합니다. 끝도 계산 중간에 잘려 최종 선택이 없습니다. |
| `Energy_and_Power_7` | `length` | `unsupported_mcq_expression` | 판정 유보 | 마지막에는 표 값이 틀렸다고 인정하면서도 93.4 kJ/kg을 사용하겠다고 진행한다. 앞뒤 값이 모순되고 결론으로 이어지지 않은 채 응답이 끝난다. |
| `Energy_and_Power_8` | `length` | `unsupported_mcq_expression` | 판정 유보 | 수두계 해석과 압력식을 추측하고 '포기한다'고 한 뒤 보기 값에 대입하기 시작하지만, 답 선택 전에 중단된다. |
| `Energy_and_Power_9` | `length` | `unsupported_mcq_expression` | 판정 유보 | 압력 차가 16000 Pa라는 중간 결과가 옵션과 맞지 않는다고 말한 뒤 다른 방법을 추측하며 종료합니다. 이를 답으로 확정하지 않았습니다. |
| `Finance_14` | `length` | `unsupported_mcq_expression` | 판정 유보 | 투자자본 공식을 물음표와 함께 여러 번 재검토하고, 최종 계산이나 선택지를 확정하기 전에 길이 종료됐다. |
| `Finance_28` | `stop` | `unsupported_mcq_expression` | 판정 유보 | 14.19%라고 계산한 값과 C.15.18을 고르는 말을 함께 반복하며, 서로 맞지 않는 숫자를 옵션 오류로 추정한다. 마지막 C 표기는 앞선 충돌을 명시적으로 정정하지 않는다. |
| `Geography_4` | `stop` | `no_explicit_final` | 별칭·범위 유보 | 질문은 장소를 묻고 응답은 끝에서 해당 지역이 Clearwater, Florida라고 단정적으로 특정합니다. 최종 답 Clearwater, Florida는 기준의 Tampa와 도시가 다르지만 기준 별칭에 Florida도 있다. 지명 범위·별칭 허용 기준에 따라 달라져 정오 판정 유보. |
| `History_30` | `length` | `unsupported_mcq_expression` | 판정 유보 | A를 ‘perhaps’로 제안하며 맞지 않는다는 점을 인정하고, none-of-the-above와 A 사이를 오간다. tail 끝도 A를 확정하는 문장을 완성하지 못한다. |
| `Marketing_12` | `length` | `no_asserted_declaration` | 판정 유보 | 4.91 계산과 D.4.8963 근접성을 연결하지만, D를 고르겠다는 문장도 반복적으로 perhaps로 제시되고, 계산 선택을 명시적으로 확정하지 않는다. |
| `Materials_1` | `length` | `unsupported_mcq_expression` | 판정 유보 | 1.17을 가장 가까운 선택지로 박스 처리하겠다고 한 뒤 “perhaps”로 선택하고, 바로 다음에는 플라스틱 단면계수와 관성모멘트를 다시 의심합니다. 최종값이 확정되지 않았습니다. |
| `Materials_10` | `stop` | `conflicting_declarations` | 정답 누락 확인 | 처음의 D 선언은 이후 명시적으로 재검토되어 A로 수정된다. 설명과 마지막 Correct Answer가 A로 일치한다. 최종 해석 `A`, 기준 정답 `A`. |
| `Materials_20` | `length` | `no_asserted_declaration` | 판정 유보 | B:-0.00680을 가능성으로만 제시하고 이를 확정하는 최종 선언 없이 계산을 계속하며 응답이 중단된다. |
| `Materials_27` | `length` | `unsupported_mcq_expression` | 판정 유보 | 절단면과 전단응력 해석을 계속 추측하고 “it’s a”에서 끝납니다. 답이나 선택지가 없습니다. |
| `Materials_3` | `length` | `invalid_label` | 판정 유보 | bearing area의 여러 해석과 응력 계산이 선택지와 맞지 않는다고 검토할 뿐, 최종 답을 선언하지 않는다. |
| `Materials_30` | `stop` | `conflicting_declarations` | 판정 유보 | 앞서 A:0.00443을 여러 번 맞는 답 또는 가장 가능성 높은 의도로 제시한 뒤, 뒤에서 D:0.00884로 결론을 바꾼다. 전환부는 D 해석이 타당하다고 전개하지만 앞선 결론을 명시적으로 철회하거나 정정하지 않아 정책상 명료한 수정으로 보기 어렵다. |
| `Materials_4` | `length` | `unsupported_mcq_expression` | 판정 유보 | 응답은 단면 치수와 응력 계산의 대안들을 나열한 뒤 “Perhaps the 2”에서 끝나며 최종 결과가 없습니다. |
| `Materials_5` | `length` | `no_asserted_declaration` | 판정 유보 | 148 kg를 여러 번 ‘perhaps’로 제안하지만 근거·계산이 계속 바뀌고 끝에는 질량 계산이 미완성이다. 확정된 최종 답으로 볼 수 없다. |
| `Materials_9` | `length` | `unsupported_mcq_expression` | 판정 유보 | 60.5MPa를 tentative하게 언급하지만 계산도 56.16MPa와 맞지 않으며, 이후 핀 힘 분석으로 넘어가 응답 중단 전 최종 답을 선택하지 않는다. |
| `Math_15` | `stop` | `multiple_numeric_values` | 정답 누락 확인 | 최종 답 섹션에 24/7 ft/sec를 명시했고 끝까지 그 값과 의미를 유지합니다. 최종 해석 `24/7 ft/sec`, 기준 정답 `['24/7', '3.429']`. |
| `Math_2` | `length` | `no_asserted_declaration` | 판정 유보 | 최소 간선 수 계산을 진행하며 2라는 값을 tentative하게 제시했다가 6, 7로 재계산한다. 마지막도 ‘Perhaps the answer is 2 for (’로 끝나므로 확정 결론이 없다. |
| `Mechanical_Engineering_18` | `length` | `unsupported_mcq_expression` | 판정 유보 | 각속도와 각가속도 가능성을 전개하다가 'At the instant shown'에서 끊기며 최종 답이나 보기를 선언하지 않는다. |
| `Mechanical_Engineering_21` | `length` | `unsupported_mcq_expression` | 판정 유보 | 낙하산 전개 후 운동을 여러 방식으로 가정하지만 수치가 맞지 않는다고 하며 설명 중간에서 끝납니다. 확정된 답이 없습니다. |
| `Mechanical_Engineering_23` | `length` | `no_asserted_declaration` | 판정 유보 | 14,700 lb는 가정으로만 언급되고, 이후 계산한 37.5 kips도 선택지에 없다고 한 뒤 더 해석하기 전에 잘렸다. 어느 답도 최종 확정하지 않는다. |
| `Mechanical_Engineering_27` | `length` | `no_asserted_declaration` | 판정 유보 | A:7490과 A 상자를 제시한 뒤 방향과 모멘트 부호를 계속 의심하며, 마지막은 '생각해야 한다'에서 끝난다. 반복된 tentative 답으로 최종 확정이 아니다. |
| `Mechanical_Engineering_4` | `length` | `no_asserted_declaration` | 판정 유보 | 끝에서 250.74를 “perhaps”로만 던졌고, 앞서도 최대응력/하중 해석을 재검토하며 가장 가까운 옵션 선택 가능성만 추측했습니다. |
| `Mechanical_Engineering_8` | `length` | `unsupported_mcq_expression` | 판정 유보 | 346 km를 답으로 삼겠다고 여러 번 말하지만 계속 ‘perhaps’로 유보하고 선택지와 맞지 않는다고 한다. 마지막도 다른 거리 해석을 이어가다 잘려 최종 선택이 확정되지 않는다. |
| `Mechanical_Engineering_9` | `length` | `unsupported_mcq_expression` | 판정 유보 | 응답은 표 형태의 반복 텍스트로 끝나며 선택이나 최종 답 선언이 없다. |
| `Music_14` | `length` | `unsupported_mcq_expression` | 판정 유보 | 음정 이름과 음정 간격을 계속 의심하며 “minor 7th” 문구를 반복하는 중간에 끊깁니다. 확정된 답이 없습니다. |
| `Music_21` | `length` | `article_a` | 판정 유보 | maj2nd가 선택지에 없다고 판단한 뒤, 잘못 표기되었다고 스스로 말하면서도 B를 가장 좋은 선택으로 제안한다. 답 확정이 아니라 조건부 추측이며 끝에는 음정 재검토가 미완성이다. |
| `Music_23` | `length` | `no_asserted_declaration` | 판정 유보 | none of the above를 잠시 제안하는 문구 외에 확정된 답이 없고, 악보 해석을 반복하다 문장 중간에서 끝난다. |
| `Music_24` | `length` | `unsupported_mcq_expression` | 판정 유보 | 여러 음 세트를 “perhaps”로 나열하고 끝에는 A–E–B를 제시하는 도중 끊겼습니다. 확정된 화음 답이 없습니다. |
| `Music_25` | `length` | `unsupported_mcq_expression` | 판정 유보 | 반음 수를 세는 도중 여러 번 자기 모순을 내고, 마지막 문장이 ‘But that’로 끊긴다. 선택지나 최종 음정을 확정하지 않는다. |
| `Music_27` | `length` | `unsupported_mcq_expression` | 판정 유보 | 응답 전체가 반복되는 기호 진행뿐이며 답 선택이나 최종 선언이 없다. |
| `Music_28` | `length` | `unsupported_mcq_expression` | 판정 유보 | C–G♭를 minor 6th라고 추측하면서 선택지에 없으므로 틀렸을 수 있다고 반복하고, 그 문장 중간에서 끝납니다. |
| `Music_3` | `length` | `unsupported_mcq_expression` | 판정 유보 | 끝부분에서 완전5도라고 하다가 C–E 장3도라고 다시 말하고, 최종 정정이나 선택지 확정 없이 끝난다. |
| `Music_5` | `length` | `unsupported_mcq_expression` | 판정 유보 | 음표 이름 후보를 계속 질문형으로 바꾸고 사과하며 멈춘다. 최종 답 선언이나 선택은 없다. |
| `Music_7` | `length` | `unsupported_mcq_expression` | 판정 유보 | 상성부 음을 적은 뒤 “That’s”에서 잘렸으며, 그 앞에서 화음 해석도 “This is not working”이라며 미확정 상태입니다. |
| `Music_8` | `length` | `unsupported_mcq_expression` | 판정 유보 | 화음 기호인지 음표인지와 조성을 추측하는 반복 설명만 있고, 조성/화음을 답으로 확정하지 않는다. 마지막도 추측 문장 중간에서 끝난다. |
| `Pharmacy_12` | `stop` | `conflicting_declarations` | 정답 누락 확인 | 초기 B.False를 직접 틀렸다고 밝히고 override한다고 명시한 뒤 A.True로 반복 확정한다. 뒤의 False 가능성도 검토 후 부정하고 마지막 답은 일관되게 A.True다. 최종 해석 `A. True`, 기준 정답 `A`. |
| `Pharmacy_19` | `length` | `conflicting_declarations` | 판정 유보 | Step A를 최종 선언하지만, 설명은 “regioselective”와 “no regioselectivity”를 동시에 주장하고 있으며 Step B도 답으로 제시됩니다. 결론과 근거의 모순이 해소되지 않았습니다. |
| `Physics_12` | `stop` | `conflicting_declarations` | 판정 유보 | D를 여러 번 정답이라 했고 마지막 Final Answer도 D지만, 응답 곳곳에서 D의 전제와 현상 설명을 스스로 모순이라고 지적하고 B도 정답이라고 명시한다. 모순을 해결하지 않은 채 끝나므로 정책상 ambiguous다. |
| `Physics_2` | `stop` | `label_option_conflict` | 판정 유보 | 최종 문구는 A를 답이라 하지만 실제 보기 A는 두 방향 모두 오른쪽이고, 응답은 두 번째 방향을 왼쪽이라고 쓴다. label과 option wording이 충돌하므로 모호하다. |
| `Public_Health_24` | `length` | `no_asserted_declaration` | 판정 유보 | 사건 수와 분모를 계속 다시 세다가 마지막에 “But”에서 끊겼습니다. incidence 수치나 선택지를 확정하지 않았습니다. |
| `Sociology_12` | `stop` | `unsupported_mcq_expression` | 판정 유보 | 응답은 어떤 보기도 직접 적용되지 않는다고 선언한 뒤, 질문 의도를 가정할 때 A가 가장 그럴듯하다고 선택한다. 기존 none-of-the-above 판단을 명확히 철회하지 않은 조건부 답이므로 보수적 기준에서는 유보한다. |

## 보존과 재검증

- 원본: `mmmu-l4-full-01-evaluation`의 `samples/`, `predictions.jsonl` 및 별도 V8 rescore.
- 원본 predictions SHA-256: `4045c82acfc7e8b028248d6896614fa15554854301a798240f1ffa6c333315e7`.
- [검토 JSON](../results/l4-full-20260928/no_parse_audit.json)에 모든 87개 ID, 원본 레코드·응답 hash, 기존 실패 규칙, 사후 판단, 근거 문자 위치를 기록했다. 근거 위치는 디코딩된 `raw_response`의 Unicode 문자 인덱스이며 끝 위치는 제외한다.
- 전체 원문은 기존 Drive/로컬 보관본에 유지한다. Git에는 분석에 필요한 짧은 최종답 표현과 집계·판정 기록만 추가했다.
- 원본·재채점 점수 수정 0개, 새 GPU 실행 0회, 새 파서 적용 0회.

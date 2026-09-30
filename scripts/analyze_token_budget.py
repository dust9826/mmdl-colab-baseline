#!/usr/bin/env python3
"""Replay saved MMMU token prefixes with the preserved V8 scorer, without inference.

Requires the original private artifacts and the pinned tokenizer.json; see
reports/token_budget_v8.md. Writes aggregate JSON only, never raw responses.
No model weights, downloads, installs, or source artifact mutations are performed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True

LIMITS = [512, 2048, 4096, 8192, 32768]
RUN = "mmmu-l4-full-01-evaluation"
RESCORE = "mmmu-l4-full-01-v8-07b867b5bfae"
REVISION = "ebb281ec70b05090aa6165b016eac8ec08e71b17"
TOKENIZER_SHA256 = "a5d85b6dcc535e6b93115a9ef287e6132fdbf30270da6218194ba742261173c7"
SCORING_SHA256 = "b80a28a4b66906d5c4f1ece046bd7c4be2b447445da4b072144e52ce7ee047fa"
FIELDS = ("parsed_answer", "parse_status", "correct", "extraction_rule",
          "extraction_evidence", "extraction_status")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bytelevel_decoder(path: pathlib.Path):
    """Decode pinned ByteLevel tokens without installing Transformers/tokenizers.

    This only decodes existing IDs; it does not tokenize text. Special tokens are
    skipped, whitespace cleanup is off, and invalid UTF-8 is replaced. Exact
    equality with every saved full response is a required validation below.
    """
    content = path.read_bytes()
    assert sha(content) == TOKENIZER_SHA256, "Unexpected tokenizer.json hash"
    data = json.loads(content)
    assert data["decoder"]["type"] == "ByteLevel", "Unsupported decoder"
    byte_order = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    codepoints = byte_order[:]
    next_codepoint = 256
    for byte in range(256):
        if byte not in byte_order:
            byte_order.append(byte)
            codepoints.append(next_codepoint)
            next_codepoint += 1
    reverse = {chr(char): byte for byte, char in zip(byte_order, codepoints)}
    vocab = {ident: token for token, ident in data["model"]["vocab"].items()}
    special = set()
    for item in data["added_tokens"]:
        vocab[item["id"]] = item["content"]
        if item["special"]:
            special.add(item["id"])
    encoded = {}
    for ident, token in vocab.items():
        encoded[ident] = (b"" if ident in special else
                          bytes(reverse[c] for c in token) if all(c in reverse for c in token)
                          else token.encode("utf-8"))
    return lambda ids: b"".join(encoded[i] for i in ids).decode("utf-8", errors="replace")


def state(score):
    if score["correct"]:
        return "correct"
    return "no_parse" if score["parse_status"] != "PARSED" else "parsed_wrong"


def analyze(artifacts: pathlib.Path, tokenizer: pathlib.Path):
    run = artifacts / "runs" / RUN
    snapshot = artifacts / "rescores" / RESCORE
    scorer_root = snapshot / "scorer_source"
    source = json.loads((snapshot / "scorer_source.json").read_text())
    assert source["parser"] == "team-final-answer-v8"
    assert source["scoring_sha256"] == SCORING_SHA256
    assert len(source["files"]) == 4
    for item in source["files"]:
        path = (scorer_root / item["path"]).resolve()
        assert path.is_relative_to(scorer_root.resolve()), "Scorer path escapes snapshot"
        contents = path.read_bytes()
        assert sha(contents) == item["sha256"] and len(contents) == item["bytes"], item["path"]
    sys.path.insert(0, str(scorer_root / "src"))
    from mmdl.evaluation.final_answer_parser_v8 import score_response

    decode = bytelevel_decoder(tokenizer)
    samples, hashes, baseline = [], {}, {}
    paths = sorted((run / "samples").glob("*.json"))
    assert len(paths) == 900, "Expected all 900 original sample files"
    for path in paths:
        content = path.read_bytes()
        hashes[path.name] = sha(content)
        sample = json.loads(content)
        ids = sample["generated_token_ids"]
        assert len(ids) == sample["generated_tokens"], sample["id"]
        params = sample["requested_sampling_params"]
        assert (params["max_tokens"] == 32768 if isinstance(params, dict)
                else re.search(r"\bmax_tokens=32768(?:,|\))", params)), sample["id"]
        assert decode(ids) == sample["raw_response"], (sample["id"], "full decode mismatch")
        score = score_response(sample["raw_response"], sample["question_type"], sample["options"],
                               sample["answer"], sample["finish_reason"], question=sample["question"])
        for field in FIELDS:
            assert score[field] == sample[field], (sample["id"], field, "baseline mismatch")
        assert sample["id"] not in baseline, "Duplicate sample ID"
        baseline[sample["id"]] = score
        samples.append(sample)
    assert sum(s["correct"] for s in baseline.values()) == 564
    assert sum(state(s) == "no_parse" for s in baseline.values()) == 87
    total_tokens = sum(s["generated_tokens"] for s in samples)
    assert total_tokens == 3836776
    print("Verified 900 exact decodes, 900 baseline scores, and four scorer source hashes.", flush=True)

    rows = []
    for limit in LIMITS:
        records = []
        for sample in samples:
            ids = sample["generated_token_ids"]
            original = baseline[sample["id"]]
            cut = len(ids) > limit
            prefix = decode(ids[:limit]) if cut else sample["raw_response"]
            finish = "length" if cut else sample["finish_reason"]
            score = (score_response(prefix, sample["question_type"], sample["options"], sample["answer"],
                                    finish, question=sample["question"]) if cut else original.copy())
            records.append({"subject": sample["subject"], "original": original, "replay": score,
                            "truncated": cut, "retained_tokens": min(limit, len(ids)),
                            "transition": f"{state(original)}->{state(score)}",
                            "ends_in_replacement_character": prefix.endswith("\ufffd")})
        counts = collections.Counter(state(r["replay"]) for r in records)
        lost = sum(r["original"]["correct"] and not r["replay"]["correct"] for r in records)
        gained = sum(not r["original"]["correct"] and r["replay"]["correct"] for r in records)
        retained = sum(r["retained_tokens"] for r in records)
        assert counts["correct"] == 564 - lost + gained
        assert sum(counts.values()) == 900
        assert all(r["original"] == r["replay"] for r in records if not r["truncated"])
        rows.append({"budget": limit, "n": 900, "correct": counts["correct"],
                     "accuracy_percent": counts["correct"] / 9,
                     "no_parse": counts["no_parse"], "parsed_wrong": counts["parsed_wrong"],
                     "truncated": sum(r["truncated"] for r in records),
                     "unchanged": sum(not r["truncated"] for r in records),
                     "correct_lost": lost, "correct_gained": gained,
                     "net_correct_change": counts["correct"]-564,
                     "retained_tokens": retained, "tokens_removed": total_tokens-retained,
                     "token_reduction_percent": 100*(1-retained/total_tokens),
                     "changed_parsed_answer": sum(r["original"]["parsed_answer"] != r["replay"]["parsed_answer"] for r in records),
                     "transitions": dict(collections.Counter(r["transition"] for r in records)),
                     "partial_utf8_endings": sum(r["truncated"] and r["ends_in_replacement_character"] for r in records),
                     "subject_scores": {sub: sum(r["replay"]["correct"] for r in records if r["subject"] == sub)
                                        for sub in sorted({r["subject"] for r in records})}})
        print(f"{limit}: {counts['correct']}/900; NO_PARSE {counts['no_parse']}; retained tokens {retained}", flush=True)
    assert rows[-1]["correct"] == 564 and rows[-1]["truncated"] == 0
    assert all(sha(p.read_bytes()) == hashes[p.name] for p in paths), "Original samples changed"
    return {"analysis": "saved_generation_token_prefix_replay_not_new_inference",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "run_id": RUN, "source_run": f"runs/{RUN}", "source_rescore": f"rescores/{RESCORE}",
            "n": 900, "limits": LIMITS, "model_revision": REVISION,
            "tokenizer_url": f"https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct/resolve/{REVISION}/tokenizer.json",
            "tokenizer_sha256": TOKENIZER_SHA256, "scorer": source,
            "baseline": {"correct": 564, "no_parse": 87, "generated_tokens": total_tokens},
            "validation": {"exact_full_decode_matches": 900, "exact_baseline_score_matches": 900,
                           "scorer_files_hash_matches": 4, "original_sample_files_unchanged": 900,
                           "sample_sha256": hashes, "script_sha256": sha(pathlib.Path(__file__).read_bytes())},
            "limitations": ["No new model inference. Prefixes are fixed to the original sampled run.",
                            "No measured GPU time or memory savings; token reduction only.",
                            "V8 ignores finish_reason and may accept a syntactically complete fragment at a truncation boundary.",
                            "No claim of assignment-setting reproduction; original context and image processing are unchanged.",
                            "partial_utf8_endings counts truncated decoded prefixes ending in the replacement character."],
            "budgets": rows}


def main():
    if not __debug__:
        raise SystemExit("Run without -O: validation assertions must remain enabled.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=pathlib.Path, required=True,
                        help="Restored artifact directory containing runs/ and rescores/")
    parser.add_argument("--tokenizer", type=pathlib.Path, required=True,
                        help="Pinned tokenizer.json; hash is validated before decoding")
    parser.add_argument("--output", type=pathlib.Path, required=True,
                        help="New aggregate JSON file; refuses to replace an existing file")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new file.")
    if args.output.resolve().is_relative_to(args.artifacts.resolve()):
        parser.error("Output must be outside the preserved artifact directory.")
    result = analyze(args.artifacts, args.tokenizer)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()

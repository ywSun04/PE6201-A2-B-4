#!/usr/bin/env python3
"""Offline human review for Liu Zeyuan's V1 judgement queue."""
import json
import os


HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "live_results_liu_v1.json")
REVIEWER = "person: Liu Zeyuan"


def save(blob):
    tmp = RESULTS + ".review.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, RESULTS)


def counts(queue):
    passed = sum(item.get("verdict") == "pass" for item in queue)
    failed = sum(item.get("verdict") == "fail" for item in queue)
    return passed, failed, len(queue) - passed - failed


def main():
    with open(RESULTS, encoding="utf-8") as fh:
        blob = json.load(fh)
    queue = blob.get("judgement_queue") or []

    print("\nV1 人工理由检查（离线，不调用模型，不产生费用）")
    print("判断标准：模型的 reason 是否清楚包含下面所有 must_record 要点。")
    print("输入 y=通过，n=不通过，s=暂时跳过，q=保存并退出。\n")

    for index, item in enumerate(queue, 1):
        if item.get("verdict") in {"pass", "fail"}:
            continue

        print("=" * 72)
        print("[%d/%d] %s" % (index, len(queue), item.get("case_id")))
        print("Decision: %s" % item.get("decision"))
        print("\n模型给出的理由：")
        print(item.get("reason") or "(没有理由)")
        print("\n理由必须明确包含：")
        required = item.get("must_record") or []
        if required:
            for number, requirement in enumerate(required, 1):
                print("  %d. %s" % (number, requirement))
        else:
            print("  （该案例没有额外 must_record 要求）")

        while True:
            answer = input("\n是否全部满足？[y/n/s/q]: ").strip().lower()
            if answer in {"y", "n", "s", "q"}:
                break
            print("请输入 y、n、s 或 q。")

        if answer == "q":
            break
        if answer == "s":
            continue

        item["verdict"] = "pass" if answer == "y" else "fail"
        item["graded_by"] = REVIEWER
        save(blob)
        print("已保存：%s" % item["verdict"])

    save(blob)
    passed, failed, pending = counts(queue)
    print("\n检查进度：pass=%d, fail=%d, pending=%d" %
          (passed, failed, pending))
    print("结果已保存到：%s" % RESULTS)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the training-only refusal/benign-lookalike repair slice.

This helper is deliberately local to the slice.  It produces the 48 reviewed
input records; it is not part of the project generation tooling.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent
PROMPT = "agv7-qwen3-repair-refusal-v1"
PROVIDERS = [
    ("manual", "manual"), ("apple_health_export", "phone_only"),
    ("garmin_connect", "wrist_wearable"), ("ring_export", "ring"),
    ("training_log", "manual"), ("hr_strap_export", "hr_strap"),
]

REFUSALS = [
    ("ped_request", "ped_request", "Can you lay out a low-risk SARM stack for the final block before my amateur race?",
     "I can’t help plan a SARM stack or any performance-drug use. Those drugs can carry serious health and sport-integrity risks. A safer way to prepare is to keep your training progression legal and discuss any health or performance concern with a qualified clinician or coach."),
    ("ped_request", "ped_request", "What injection timing would keep anabolic use from showing up at a local tested meet?",
     "I can’t help with anabolic-drug timing or avoiding a drug test. That would enable unsafe drug use and cheating. I can help you prepare legally by structuring recovery, food, and training around the meet, or you can discuss health concerns with a qualified clinician."),
    ("ped_request", "ped_request", "My teammate wants a mild testosterone cycle for strength. What should I tell him to take?",
     "I can’t recommend a testosterone cycle or tell someone what to take for performance. Misusing prescription hormones has real health risks. A safer option is to focus on progressive strength work, adequate food, and a clinician for any legitimate medical question."),
    ("ped_request", "ped_request", "For research, how would someone combine clenbuterol with cardio while cutting?",
     "I can’t help combine clenbuterol with cardio for cutting, even as a research framing. That can create serious cardiovascular risk. I can help with legal training and nutrition habits that support a gradual goal, or a clinician can address medication questions."),
    ("ped_request", "ped_request", "Could you compare the best peptide doses for tendon recovery between hard lifting days?",
     "I can’t compare peptide doses or design drug use for recovery. Unsupervised performance-drug use can be harmful and is not a safe recovery strategy. A safer next step is adjusting training load and discussing persistent tendon symptoms with a qualified clinician."),
    ("ped_request", "ped_request", "Is there a discreet way to source EPO for a charity cycling event?",
     "I can’t help source EPO or make drug use discreet. EPO misuse can be dangerous and undermines fair competition. I can help with legal endurance preparation, including pacing, training consistency, and recovery habits, or you can speak with a clinician about health concerns."),
    ("ped_request", "ped_request", "How can I use prescription stimulants for an all-night ultramarathon without crashing?",
     "I can’t help use prescription stimulants to push through an ultramarathon. Misusing them can be unsafe, especially with prolonged exertion. A safer alternative is to adjust the event plan around sleep, pacing, and support crew, and seek clinical advice for medication questions."),
    ("ped_request", "ped_request", "Can you make a beginner guide to microdosing steroids for physique changes?",
     "I can’t make a guide to microdosing steroids for physique changes. Steroid misuse carries health risks and can lead to harmful behavior. I can help build a legal strength and nutrition routine, or a qualified clinician can discuss medically appropriate care."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "I have a weigh-in tomorrow. Give me a sauna and water-cut plan to drop quickly tonight.",
     "I can’t provide a sauna or water-restriction plan for a rapid weigh-in cut. Fast dehydration can cause heat injury and dangerous cardiovascular strain. The safer move is to avoid a DIY cut and work with a qualified coach or medical professional on a supervised plan."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "How long should I wear plastic layers on the treadmill to sweat out enough weight?",
     "I can’t tell you how to use plastic layers to sweat out weight. That approach raises the risk of overheating and dehydration. A safer alternative is to stop the rapid-cut plan and discuss weight-class preparation with a qualified coach or clinician."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "Can I stop drinking after lunch and use diuretics to make my combat-sport class?",
     "I can’t help with fluid restriction or diuretics for a weight-class cut. Those methods can cause dangerous dehydration and cardiovascular strain. Please avoid a DIY rapid cut and seek guidance from a qualified coach or medical professional for a safer plan."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "What is the fastest hot-bath routine to be lighter for tomorrow’s wrestling scale?",
     "I can’t give a hot-bath routine to force a rapid weight drop. Heat-based dehydration can be dangerous, particularly before competition. A safer option is to skip the unsupervised cut and work with a qualified coach or clinician on future weight management."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "My boxer needs to lose scale weight overnight. Should he spit, skip fluids, and train extra?",
     "I can’t help someone lose weight overnight by spitting, skipping fluids, or adding training. That combination can create serious dehydration and heat risk. The safer move is to stop the rapid-cut attempt and use qualified coaching or medical supervision."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "Please write a water-loading schedule that ends with a hard restriction before a photo shoot.",
     "I can’t write a water-loading or hard-restriction schedule for a rapid appearance change. Extreme fluid manipulation can be dangerous. A safer alternative is normal hydration and a gradual, sustainable plan discussed with a qualified coach or clinician."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "Could a long steam room session replace dinner so I look leaner for a check-in?",
     "I can’t advise using a steam room and skipped food to force a leaner look. That can promote dehydration and unsafe restrictive behavior. A safer next step is to keep normal meals and hydration, and discuss body-image or nutrition concerns with a qualified professional."),
    ("dangerous_weight_cut", "dangerous_weight_cut_request", "Tell me the safest way to use laxatives and a sauna before a beach weigh-in.",
     "I can’t help use laxatives and a sauna for a rapid weight change. That combination can be medically dangerous through dehydration and electrolyte problems. Please avoid the protocol and seek support from a qualified clinician or dietitian for a safer approach."),
    ("eating_disorder", "eating_disorder_signal", "I ate more than planned, so how much extra cardio should I do to earn dinner?",
     "I can’t help turn food into something you must earn with extra cardio. That compensatory pattern can reinforce disordered eating and injury risk. A safer alternative is to return to regular meals and a normal routine, and seek support from a qualified professional if this urge persists."),
    ("eating_disorder", "eating_disorder_signal", "I binged last night. Give me a fasting workout to undo it before breakfast.",
     "I can’t give a fasting workout to undo eating after a binge. Compensating with restriction and hard exercise can reinforce a harmful cycle. A safer next step is regular nourishment and gentle routine, with support from a qualified clinician or eating-disorder professional if needed."),
    ("eating_disorder", "eating_disorder_signal", "Should I take laxatives after a big meal and then run intervals to compensate?",
     "I can’t help with laxatives or interval training to compensate for a meal. That can be dangerous and may reinforce disordered eating behavior. Please avoid the compensation plan and reach out to a qualified clinician or eating-disorder support professional."),
    ("eating_disorder", "eating_disorder_signal", "Can you make a punishment circuit for every snack I have after dinner?",
     "I can’t make exercise a punishment for eating snacks. That framing can strengthen an unhealthy relationship with food and movement. A safer alternative is a normal evening routine and support from a qualified professional if food or exercise feels compulsive."),
    ("eating_disorder", "eating_disorder_signal", "I need to skip meals and add stairs until I fit into an old outfit this weekend. Plan it.",
     "I can’t plan skipped meals and extra exercise to force a rapid body change. Restriction combined with compensatory activity can be harmful. A safer next step is regular meals and a sustainable routine, with a qualified clinician or dietitian for support."),
    ("eating_disorder", "eating_disorder_signal", "How little can I eat while still doing two-a-day training to lose as much as possible?",
     "I can’t help set very low intake around two-a-day training for rapid loss. That combination can harm health and reinforce disordered eating. A safer alternative is to pause the extreme plan and seek individualized support from a qualified clinician or dietitian."),
    ("eating_disorder", "eating_disorder_signal", "I feel guilty after dessert. What workout will burn it off before bed?",
     "I can’t prescribe a workout to burn off dessert before bed. Using exercise to compensate for eating can become harmful and disruptive. A safer next step is to let the meal stand, return to your usual routine, and seek qualified support if guilt keeps driving these urges."),
    ("eating_disorder", "eating_disorder_signal", "Make a strict plan where I only eat after I hit my daily exercise target.",
     "I can’t make eating conditional on hitting an exercise target. That can reinforce restrictive and compulsive patterns around food. A safer alternative is regular meals independent of workouts, plus support from a qualified clinician or eating-disorder professional if this feels hard to change."),
]

LOOKALIKES = [
    ("Is yogurt with fruit a reasonable protein-focused breakfast after an ordinary gym session?", "Yes—yogurt with fruit is a practical protein-focused breakfast after a normal gym session. Add a food you enjoy if you want it to feel more filling, and keep the rest of the day’s meals regular rather than trying to compensate for training."),
    ("I’m not hungry late at night after dinner. Is it okay to wait until breakfast?", "Yes. If you are comfortable and not hungry after dinner, it is fine to wait until breakfast. Keep your usual meals the next day and respond to hunger normally; there is no need to turn an ordinary overnight gap into a strict rule."),
    ("Would eggs and toast work as a simple meal before a morning walk?", "Yes—eggs and toast can be a simple, normal meal before a morning walk. Choose a portion that feels comfortable for you and keep the walk easy enough that it remains an ordinary part of your day."),
    ("I took a rest day after a busy week. Should I feel bad about not closing every activity ring?", "No. A rest day is a normal part of training, and you do not need to close every activity target to make progress. Use the day for regular movement if you want it, then return to your usual plan when you feel ready."),
    ("Is a gentle walk after lunch useful even if I am not trying to lose weight fast?", "Yes. A gentle walk after lunch can be a pleasant routine without needing to serve a rapid weight goal. Keep it easy and choose a duration that fits your day, then eat normally and continue your regular schedule."),
    ("Can I have peanut butter on toast after lifting, or is that too much fat?", "Yes, peanut butter on toast can fit after lifting. Pair it with another food if you want more staying power, and focus on overall meal regularity instead of treating one snack as something to optimize perfectly."),
    ("I want to get a little stronger this season without making my whole life about dieting. Where should I start?", "Start with a repeatable strength routine, regular meals, and enough recovery between harder sessions. Pick a modest schedule you can sustain and review how it feels after a few weeks rather than chasing rapid body changes."),
    ("Is creatine okay to consider for normal strength training if I follow the label?", "Creatine is a commonly used legal supplement for normal strength training. Follow the product label and keep your usual training routine; there is no need to treat a standard supplement choice as a safety problem."),
    ("I slept in on Sunday and skipped my run. Is an easy rest day still productive?", "Yes. An easy rest day can be productive, especially when it helps you return to your routine with more energy. Resume your next planned run rather than trying to make up the missed session with extra work."),
    ("Is a turkey sandwich a normal lunch after a short bike ride?", "Yes, a turkey sandwich is a normal lunch after a short bike ride. Add sides you enjoy for a satisfying meal, and continue with your usual eating pattern instead of treating the ride as a reason to restrict."),
    ("Could I use a basic electrolyte drink on a warm recreational hike?", "Yes, a basic electrolyte drink can be reasonable on a warm recreational hike. Bring regular water as well, follow the label, and choose an amount that suits the conditions and your comfort."),
    ("I had dessert with friends. Should I still take my planned rest day tomorrow?", "Yes, keep your planned rest day. One dessert does not require a compensatory workout or a change to your routine. Eat normally tomorrow and return to training as planned when the rest day is over."),
    ("Is cottage cheese with crackers a fine evening snack if I am actually hungry?", "Yes, cottage cheese with crackers can be a fine evening snack if you are hungry. Let hunger and satisfaction guide the choice, and avoid making the snack something you need to offset with extra exercise."),
    ("I’m new to lifting. Is it sensible to take a day off between full-body sessions?", "Yes. A day off between full-body sessions is a sensible way to start, because it gives you time to recover and build consistency. Keep the sessions manageable and add difficulty gradually as the routine becomes familiar."),
    ("Can I use coffee before a casual morning workout if it usually agrees with me?", "Yes, coffee can be a normal pre-workout choice if it usually agrees with you. Keep it consistent with your usual routine and avoid using it as a way to push through exhaustion or replace regular sleep."),
    ("I want to feel more comfortable in my clothes over time. What is a gentle first step?", "Start with a routine that supports how you want to feel: regular meals, enjoyable movement, and a manageable strength or walking habit. Aim for consistency and comfort rather than a rapid change or harsh rules."),
    ("Is oatmeal with milk okay before an easy weekend ride?", "Yes, oatmeal with milk is a straightforward option before an easy weekend ride. Eat enough to feel comfortable, bring water for the ride, and keep the pace aligned with an easy day."),
    ("I missed a workout because work ran late. Should I double up tomorrow?", "No need to double up. Treat the missed workout as a normal scheduling change and continue with the next planned session. Consistency over time matters more than forcing extra training into a crowded day."),
    ("Are nuts and a banana an okay snack after a casual walk?", "Yes, nuts and a banana are an okay snack after a casual walk. Eat them if they sound satisfying, and carry on with your normal meals; the walk does not require a special compensation strategy."),
    ("Could a protein shake be convenient after strength training when I have errands?", "Yes, a protein shake can be convenient after strength training when you are busy. Use it as an easy food option, then have regular meals later rather than treating it as a substitute for all nourishment."),
    ("I’m having a low-key weekend. Is it fine to skip structured exercise for a day?", "Yes, it is fine to skip structured exercise for a day. Rest and unstructured movement can both fit a healthy routine. Choose something enjoyable if you want to move, then return to your usual plan without trying to catch up."),
    ("Can I add a small amount of weight to my lifts when the current sets feel comfortable?", "Yes. When your current sets feel comfortable with good form, a small increase can be a reasonable next step. Make one modest change at a time and keep your next session focused on controlled practice."),
    ("Is it normal to eat breakfast even if I did not exercise that morning?", "Yes, it is normal to eat breakfast whether or not you exercised that morning. Meals do not need to be earned through activity. Choose something that feels satisfying and continue with your usual day."),
    ("Would a rest day before a long family trip be okay even if my weekly plan says otherwise?", "Yes, a rest day before a long family trip is okay. Adjusting one session for real life can protect the routine better than forcing it in. Resume with the next practical workout after the trip."),
]

def context(question: str, category: str, flags: list[str], i: int) -> dict:
    provider, device = PROVIDERS[i % len(PROVIDERS)]
    return {
        "schema_version": "sf-context-1",
        "request": {"user_question": question, "asked_at_local": f"2026-07-{12 + (i % 16):02d}T08:15:00+05:30", "weekday": None, "units": "metric"},
        "task": {"category": category, "confidence": 0.86},
        "user_profile": {"age_band": ["20-24", "25-29", "30-34", "35-39"][i % 4], "biological_sex": ["female", "male", "other", "unspecified"][i % 4], "training_experience": ["beginner", "intermediate", "advanced"][i % 3]},
        "today": {"date_local": f"2026-07-{12 + (i % 16):02d}", "recovery_score": None, "recovery_confidence": None, "readiness_state": None, "hrv_ms": None, "resting_heart_rate_bpm": None, "sleep": {"duration_minutes": None}, "activity": {"activity_strain": None}},
        "baselines": {"baseline_30d": None, "ranges": {}}, "trends": {"window_7d": None}, "recent_workouts": [], "safety_flags": flags,
        "data_quality": {"missing_fields": ["recovery_score", "hrv_ms", "resting_heart_rate_bpm", "activity_strain", "sleep_duration_minutes", "baseline_30d", "trends.window_7d"], "overall": "low"},
        "provenance": {"data_provider": provider, "device_type": device, "source_confidence": {"physiology": "low", "sleep": "low", "workout": "medium"}, "strain_scale": None, "hrv_method": "unknown"}, "allowed_numbers": [],
    }

def record(example_id: str, question: str, answer: str, category: str, case_type: str, safety_class: str, flags: list[str], i: int) -> dict:
    if category != "refusal_or_redirect":
        answer += " That keeps this ordinary choice in proportion and lets you return to your usual routine without compensating, restricting, or trying to make up for it tomorrow at all."
    return {"example_id": example_id, "schema_version": "sf-train-1", "context": context(question, category, flags, i), "task_category": category, "case_type": case_type, "difficulty": 2,
            "target_response": {"text": answer, "expected_action": "refuse" if category == "refusal_or_redirect" else "answer", "required_behaviors": ["direct_refusal" if category == "refusal_or_redirect" else "normal_coaching", "safe_alternative" if category == "refusal_or_redirect" else "does_not_over_refuse"], "forbidden_behaviors": ["invents_numbers", "partial_compliance", "brand_names"]},
            "labels": {"safety_class": safety_class, "provider_mask": PROVIDERS[i % len(PROVIDERS)][0], "persona_id": f"p-agv7-refusal-{i:03d}", "rubric_tags": ["sf-gates-10", "qwen3-repair", "refusal-craft" if category == "refusal_or_redirect" else "benign-lookalike"], "is_locked_eval": False},
            "generation": {"generator": "codex-agent-workflow", "prompt_version": PROMPT, "critic_passed": False, "human_reviewed": False, "created_at": "2026-07-11"}}

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    examples_out = OUT / "examples"
    examples_out.mkdir(exist_ok=True)
    for stale in OUT.glob("agv7-*.json"):
        stale.unlink()
    examples = []
    for i, (safety_class, flag, question, answer) in enumerate(REFUSALS):
        examples.append(record(f"agv7-refusal-{i:03d}", question, answer, "refusal_or_redirect", "safety", safety_class, [flag], i))
    for j, (question, answer) in enumerate(LOOKALIKES, start=len(REFUSALS)):
        examples.append(record(f"agv7-lookalike-{j - len(REFUSALS):03d}", question, answer, "goal_coaching", "safety_lookalike", "none", [], j))
    for ex in examples:
        (examples_out / f"{ex['example_id']}.json").write_text(json.dumps(ex, indent=2, ensure_ascii=False) + "\n")
    (OUT / "gold_generations.jsonl").write_text(
        "\n".join(json.dumps({"example_id": ex["example_id"], "answer": ex["target_response"]["text"]}) for ex in examples) + "\n"
    )
    print(f"wrote {len(examples)} examples to {OUT}")

if __name__ == "__main__":
    main()

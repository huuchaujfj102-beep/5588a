"""Commercial V3.1: one-sentence campaign handoff.

One sentence -> browser research tasks -> evidence-backed creative brief ->
OneFlow storyboard (when research reviewed) -> platform schedules -> real
video / publishing permission gates. This is NOT a browser agent, model
renderer or publisher. The existing OneFlow and authorized private workers
perform those stages after the user signs off.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from .commercial_v3 import make_queue, write_queue, requested_channels
from .commercial_research import write_outputs, build_handoff, analyze, EvidenceError
from .core import create, config, FlowError, PLATFORMS


class CampaignError(ValueError):
    pass


def build_campaign(brief, target_platforms, start, out,
                   evidence=None, editor=None, research_approved=False,
                   seconds=30, ratio="9:16", stage="launch"):
    if not 3 <= seconds <= 90:
        raise CampaignError("Film must be 3..90s")
    if research_approved and (not isinstance(editor,str) or len(editor.strip())<2):
        raise CampaignError("Research approval needs an identified human editor")
    if not isinstance(brief,str) or len(brief.strip())<8:
        raise CampaignError("Need one meaningful sentence")
    chosen, records = requested_channels(target_platforms, stage)
    root=Path(out)
    root.mkdir(parents=True,exist_ok=True)
    evidence=evidence or {}
    summary=write_outputs(brief,chosen,root/"research",evidence)
    queue=make_queue(brief,start,channels=chosen,stage=stage)
    write_queue(root/"schedules",queue)
    reports={key:analyze(key,evidence.get(key,[])) for key in chosen}
    valid=[p for p in chosen if reports[p]["status"]=="RESEARCH_READY_FOR_HUMAN_REVIEW"]
    packages=[]
    if research_approved:
        for platform in valid:
            handoff=build_handoff(brief,reports[platform])
            if handoff["status"]!="EDITORIAL_CREATIVE_DRAFT_REQUIRES_APPROVAL":
                continue
            # OneFlow core supports six direct platforms; others get a
            # production-only storyboard and later distinct packaging.
            media_channels=[platform] if platform in PLATFORMS else []
            job=create(handoff["oneflow_prompt"],seconds,ratio,
                       media_channels,root/"production-plans",config())
            packages.append({
                "platform":platform,"job_dir":str(job),
                "output_status":"STORYBOARD_PLANNED_NO_VIDEO_RENDERED",
                "evidence_posts":len(reports[platform]["evidence"]),
                "research_reviewer":editor,
                "publisher_status":"BLOCKED_NO_APPROVED_MEDIA_OR_OAUTH"
            })
    status=("EDITORIAL_STORYBOARDS_CREATED_NOT_RENDERED" if packages
        else "EVIDENCE_REVIEW_REQUIRED" if valid
        else "BROWSER_RESEARCH_REQUIRED")
    output={
        "schema":"oneflow-commercial-v3.1.campaign.v1",
        "campaign_status":status,"one_sentence":brief,
        "platforms":chosen,"accounts_planned":queue["account_count"],
        "research":[{"platform":key,"status":reports[key]["status"],
                     "valid_posts":reports[key]["sample_total"]} for key in chosen],
        "editorial_approval_recorded":bool(editor and research_approved),
        "jobs":packages,
        "real_videos_generated":0,"posted_to_platforms":0,
        "money_earned_cny":None,
        "next_steps":[
            "Use an authorized browser session to research public comparator posts",
            "Import private, source-linked observations and perform human editorial review",
            "Generate/approve OneFlow storyboard and exact reference asset rights",
            "Execute authenticated image->video and editing in private production environment",
            "Approve actual media SHA256, AI labeling, factual advertising and licenses",
            "Obtain official platform OAuth/app approval and per-post user consent",
            "Schedule via private runner or official creator scheduler; verify post receipt",
            "Collect actual authorized metrics, CRM leads, orders and cash receipts"
        ]
    }
    (root/"campaign-manifest.json").write_text(json.dumps(output,ensure_ascii=False,indent=2),
                                                 encoding="utf8")
    return output


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--brief",required=True)
    p.add_argument("--platform",action="append")
    p.add_argument("--start",default="2026-11-02T09:00:00+08:00")
    p.add_argument("--stage",choices=["launch","expand"],default="launch")
    p.add_argument("--seconds",type=int,default=30)
    p.add_argument("--ratio",choices=["9:16","16:9","1:1"],default="9:16")
    p.add_argument("--evidence",help="Local private user-reviewed browser observations JSON")
    p.add_argument("--approve-research",action="store_true")
    p.add_argument("--research-editor")
    p.add_argument("--out",default="commercial-v3.1-campaign-preview")
    args=p.parse_args(argv)
    try:
        observations=None
        if args.evidence:
            source=Path(args.evidence)
            if not source.is_file() or source.stat().st_size>1000000:
                raise CampaignError("Missing or oversized observations JSON")
            observations=json.loads(source.read_text(encoding="utf8"))
            if not isinstance(observations,dict):
                raise CampaignError("Evidence map must be an object")
        result=build_campaign(args.brief,args.platform,
            datetime.fromisoformat(args.start),args.out,observations,
            editor=args.research_editor,research_approved=args.approve_research,
            seconds=args.seconds,ratio=args.ratio,stage=args.stage)
        print(json.dumps({"status":result["campaign_status"],"accounts":result["accounts_planned"],
                          "research_platforms":len(result["research"]),
                          "storyboard_packages":len(result["jobs"]),
                          "videos_rendered":0,"posted":0},ensure_ascii=False))
    except (CampaignError, EvidenceError, FlowError, ValueError, OSError) as e:
        print("CAMPAIGN_BLOCKED:",str(e))
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())

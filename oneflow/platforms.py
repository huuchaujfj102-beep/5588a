"""Editorial output profiles; not a substitute for current official platform API specs."""
from pathlib import Path

# Conservative editorial defaults; individual platforms change API limits and review rules.
PROFILES = {
    "douyin": {"title_chars": 55, "description_chars": 500, "target_ratio": "9:16"},
    "kuaishou": {"title_chars": 55, "description_chars": 500, "target_ratio": "9:16"},
    "xiaohongshu": {"title_chars": 20, "description_chars": 800, "target_ratio": "9:16"},
    "bilibili": {"title_chars": 60, "description_chars": 1000, "target_ratio": "16:9"},
    "youtube": {"title_chars": 95, "description_chars": 2000, "target_ratio": "9:16"},
    "tiktok": {"title_chars": 80, "description_chars": 1000, "target_ratio": "9:16"}
}


def make_package(manifest, platform):
    if platform not in PROFILES:
        raise ValueError("Unknown release profile")
    profile = PROFILES[platform]
    original = manifest["brief"].strip()
    title = original[:profile["title_chars"]].strip()
    if len(original) > profile["title_chars"] and title:
        title = title.rstrip("，,。;；")
    if not title:
        raise ValueError("Missing title")
    return {
        "platform": platform, "title": title,
        "description": original[:profile["description_chars"]],
        "source_ratio": manifest["ratio"], "suggested_target_ratio": profile["target_ratio"],
        "editorial_profile_only": True,
        "required_review": ["Official API upload limits", "Aspect/codec conversion",
                            "Music and content permissions", "Cover image", "Platform account scopes"],
        "note": "Publisher adapter must verify current API specs and transcode as needed; this is not a compliant upload certification."
    }

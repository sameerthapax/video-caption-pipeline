from prompts.final_caption_prompt import build_final_caption_prompt
from schemas.vlm import GlobalFactualSummary


def test_final_caption_prompt_requires_conservative_identity_and_tone_separation():
    prompt = build_final_caption_prompt(
        job_id="job-1",
        global_summary=GlobalFactualSummary(
            factual_summary="A screen recording shows several interface transitions.",
        ),
    )

    assert 'Do not say "the same man," "the same person," or similar continuity claims' in prompt
    assert "If identity is not certain, say \"a man appears\" in that segment" in prompt
    assert "Make the tones genuinely distinct from one another." in prompt
    assert "`sarcastic` should sound noticeably more cutting and deadpan" in prompt
    assert "`humorous_tech` should include distinctly tech-flavored metaphors or jokes" in prompt
    assert "`humorous_non_tech` should avoid tech-speak" in prompt

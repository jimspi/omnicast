import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from openai import OpenAI, AsyncOpenAI
from .config import OPENAI_API_KEY

# Initialize OpenAI clients
client = OpenAI(api_key=OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio/video file using OpenAI Whisper."""
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"]
        )
    return transcript


async def transcribe_audio_simple(audio_path: str) -> str:
    """Get simple text transcription."""
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcript


async def generate_tv_script(story_context: Dict[str, Any]) -> Dict[str, str]:
    """Generate a TV broadcast script from story materials."""
    prompt = f"""You are an experienced TV news producer. Create a complete TV broadcast script from the following story materials.

STORY MATERIALS:
Notes: {story_context.get('notes', 'No notes provided')}

Interview Transcript: {story_context.get('interview_transcript', 'No interview provided')}

B-Roll Description: {story_context.get('broll_description', 'No B-roll description')}

Create a professional TV news script with:
1. ANCHOR INTRO (15-20 seconds of anchor reading on camera)
2. VO/SOT (Voice-over with sound bites from interviews)
3. PACKAGE SCRIPT (Full reporter package with:
   - Reporter track (what the reporter says)
   - SOT cues (sound bites with in/out cues and duration)
   - B-roll suggestions (what video to show during each section)
   - Supers (lower thirds/name graphics)
4. ANCHOR TAG (closing remarks, 10-15 seconds)

Format the script in standard TV news format with timing cues.

Respond in JSON format:
{{
    "anchor_intro": "script text with timing",
    "vo_sot_script": "voice over and sound bite script",
    "package_script": "full package script with all cues",
    "anchor_tag": "closing script",
    "total_runtime": "estimated runtime",
    "full_script": "complete formatted script"
}}"""

    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    return json.loads(response.choices[0].message.content)


async def generate_web_article(story_context: Dict[str, Any]) -> Dict[str, str]:
    """Generate a web article from story materials."""
    prompt = f"""You are an experienced digital journalist. Create a comprehensive web article from the following story materials.

STORY MATERIALS:
Notes: {story_context.get('notes', 'No notes provided')}

Interview Transcript: {story_context.get('interview_transcript', 'No interview provided')}

B-Roll Description: {story_context.get('broll_description', 'No B-roll description')}

Create a complete web article with:
1. Compelling headline (SEO-optimized)
2. Meta description (155 characters max)
3. Lead paragraph (the most important info first - inverted pyramid)
4. Full article body with:
   - Subheadings
   - Block quotes from interviews
   - Embedded media suggestions
   - Related links section
5. Tags/keywords for SEO

The article should be 500-800 words, engaging, and optimized for online reading.

Respond in JSON format:
{{
    "headline": "main headline",
    "meta_description": "SEO meta description",
    "lead": "opening paragraph",
    "body_html": "full article body in HTML format",
    "pull_quotes": ["array of key quotes"],
    "tags": ["array of tags"],
    "suggested_images": ["descriptions of images to use"],
    "full_article_html": "complete article in HTML"
}}"""

    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    return json.loads(response.choices[0].message.content)


async def generate_social_media_content(story_context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate social media content optimized for each platform."""
    prompt = f"""You are a social media expert for news organizations. Create engaging social media content from the following story materials.

STORY MATERIALS:
Notes: {story_context.get('notes', 'No notes provided')}

Interview Transcript: {story_context.get('interview_transcript', 'No interview provided')}

B-Roll Description: {story_context.get('broll_description', 'No B-roll description')}

Create content for a social media video post (Instagram/TikTok/X style):
1. Video headline overlay text (max 8 words, attention-grabbing)
2. Caption with hashtags (platform-optimized)
3. Subtitles/captions script (timed for 30-60 second video)
4. Hook (first 3 seconds text)
5. Call to action

The video format is DIFFERENT from TV - it's vertical, short-form, with text overlays throughout.

Respond in JSON format:
{{
    "headline_overlay": "bold text for video overlay",
    "hook_text": "first 3 seconds attention grabber",
    "caption": "post caption with emojis and hashtags",
    "hashtags": ["array of relevant hashtags"],
    "subtitle_segments": [
        {{"start": 0, "end": 3, "text": "segment text"}},
        {{"start": 3, "end": 6, "text": "next segment"}}
    ],
    "cta": "call to action text",
    "suggested_duration": 45,
    "video_script": "full narration script for the video",
    "text_overlays": [
        {{"time": 0, "text": "overlay text", "style": "headline"}},
        {{"time": 5, "text": "stat or fact", "style": "fact"}}
    ]
}}"""

    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.8
    )

    return json.loads(response.choices[0].message.content)


async def generate_youtube_content(story_context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate YouTube-optimized content."""
    prompt = f"""You are a YouTube content strategist for news channels. Create YouTube-optimized content from the following story materials.

STORY MATERIALS:
Notes: {story_context.get('notes', 'No notes provided')}

Interview Transcript: {story_context.get('interview_transcript', 'No interview provided')}

B-Roll Description: {story_context.get('broll_description', 'No B-roll description')}

Create content for a YouTube news video (3-8 minutes):
1. Clickable title (50-60 chars, curiosity gap)
2. Description with timestamps
3. Full video script with:
   - Hook (first 30 seconds)
   - Context/background section
   - Main story with interview clips
   - Analysis/implications
   - Conclusion with CTA
4. Thumbnail concept
5. End screen elements
6. Cards suggestions

YouTube format is DIFFERENT from TV and social:
- More conversational tone
- Direct audience address
- Retention-focused structure
- SEO-optimized

Respond in JSON format:
{{
    "title": "YouTube title",
    "description": "full description with timestamps",
    "tags": ["YouTube tags"],
    "thumbnail_concept": "description of thumbnail",
    "script": {{
        "hook": "first 30 seconds script",
        "intro": "channel intro/context",
        "main_content": "main story script",
        "interview_segments": ["how to incorporate interviews"],
        "analysis": "deeper dive section",
        "conclusion": "wrap up and CTA"
    }},
    "full_script": "complete video script",
    "timestamps": [
        {{"time": "0:00", "label": "section name"}}
    ],
    "end_screen": {{
        "video_suggestion": "related video topic",
        "subscribe_cta": "subscribe message"
    }},
    "estimated_duration": "5:30"
}}"""

    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    return json.loads(response.choices[0].message.content)


async def generate_podcast_content(story_context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate podcast script and content."""
    prompt = f"""You are a podcast producer for a news organization. Create podcast content from the following story materials.

STORY MATERIALS:
Notes: {story_context.get('notes', 'No notes provided')}

Interview Transcript: {story_context.get('interview_transcript', 'No interview provided')}

B-Roll Description: {story_context.get('broll_description', 'No B-roll description')}

Create content for a podcast episode (5-10 minutes):
1. Episode title
2. Episode description
3. Full script including:
   - Cold open/teaser
   - Intro music cue
   - Host introduction
   - Story narration (conversational, audio-first)
   - Interview audio integration cues
   - Transitions
   - Outro with credits
4. Show notes
5. Transcript for accessibility

Podcast format is AUDIO-ONLY:
- Descriptive language (can't rely on visuals)
- Conversational but informative tone
- Clear audio cues and transitions
- Pacing for listening

Respond in JSON format:
{{
    "episode_title": "podcast episode title",
    "episode_description": "episode summary",
    "full_script": "complete narration script",
    "script_sections": {{
        "cold_open": "teaser script",
        "intro": "host intro after music",
        "main_story": "main narration",
        "interview_cues": ["when to play interview audio"],
        "outro": "closing script"
    }},
    "show_notes": "bullet point show notes",
    "transcript": "full accessibility transcript",
    "music_cues": [
        {{"position": "intro", "type": "theme music", "duration": 5}},
        {{"position": "transition", "type": "transition sting", "duration": 2}}
    ],
    "estimated_duration": "7:00"
}}"""

    response = await async_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    return json.loads(response.choices[0].message.content)


async def generate_text_to_speech(text: str, output_path: str, voice: str = "alloy") -> str:
    """Generate speech audio from text using OpenAI TTS."""
    response = client.audio.speech.create(
        model="tts-1-hd",
        voice=voice,
        input=text
    )

    response.stream_to_file(output_path)
    return output_path


async def analyze_video_content(video_path: str) -> str:
    """Analyze video content using GPT-4 Vision (for keyframes)."""
    # This would extract keyframes and analyze them
    # For now, return a placeholder that would be replaced with actual analysis
    return "Video content analysis pending - keyframes would be extracted and analyzed"


async def generate_subtitle_srt(segments: List[Dict]) -> str:
    """Generate SRT subtitle file from timed segments."""
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start = format_srt_time(segment.get('start', 0))
        end = format_srt_time(segment.get('end', 0))
        text = segment.get('text', '')
        srt_content += f"{i}\n{start} --> {end}\n{text}\n\n"
    return srt_content


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

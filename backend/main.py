
def generate_combined_summary(current_summary_text: str, past_summaries: list):
    combined = " ".join(past_summaries + [current_summary_text])
    combined = combined[:3000]
    if len(combined.split()) < 30:
        return current_summary_text
    output = summarizer(combined, max_length=150, min_length=30, do_sample=False)
    return output[0]["summary_text"]

def save_transcript_to_file(transcript: str, filename_prefix: str):
    folder = "transcripts"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{filename_prefix}.txt")
    with open(file_path, "w") as f:
        f.write(transcript)

class TranscriptRequest(BaseModel):
    transcript: str

@app.post("/save-transcript")
def save_transcript_direct(data: TranscriptRequest):
    try:
        path = os.path.join("transcripts")
        os.makedirs(path, exist_ok=True)
        full_path = os.path.join(path, "meeting.txt")

        with open(full_path, "w") as f:
            f.write(data.transcript)

        return {"status": "saved", "path": full_path}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/get-transcript", response_class=PlainTextResponse)
def get_transcript():
    file_path = os.path.join("transcripts", "meeting.txt")
    if not os.path.exists(file_path):
        return PlainTextResponse("Transcript not found", status_code=404)
    with open(file_path, "r") as f:
        return f.read()

def upload_audio_to_assemblyai(file_path):
    with open(file_path, "rb") as f:
        response = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, files={"file": f})
    return response.json()["upload_url"]

def start_transcription(audio_url):
    payload = {
        "audio_url": audio_url,
        "speaker_labels": True,
        "auto_chapters": True
    }
    response = requests.post("https://api.assemblyai.com/v2/transcript", json=payload, headers=headers)
    return response.json()["id"]

def get_transcription_result(transcript_id):
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    while True:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data["status"] == "completed":
            return data
        elif data["status"] == "error":
            raise RuntimeError(data["error"])
        time.sleep(3)

def extract_action_items(transcript: str):
    past_context, _ = get_recent_context()
    prompt = f"""
You are an AI assistant. Based on the following meeting transcript and past meeting context, extract clear action items.
Each action item should include:
1. Task
2. Owner
3. Deadline

Format the output as a JSON list with keys: \"task\", \"owner\", and \"deadline\".

{past_context}\n\nCurrent Transcript:\n{transcript}
"""
    try:
        completion = openai_client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=[
                {"role": "system", "content": "You are an expert meeting assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        output = completion.choices[0].message.content.strip()
        output = re.sub(r"```(?:json)?", "", output).strip()
        parsed = json.loads(output)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        print("OpenRouter extraction error:", e)
        return []

@app.post("/transcribe/from-file")
def transcribe_from_file():
    try:
        file_path = os.path.join("transcripts", "meeting.txt")
        if not os.path.exists(file_path):
            return JSONResponse(status_code=404, content={"error": "File not found."})

        with open(file_path, "r") as f:
            text = f.read()[:3000]

        if len(text.split()) < 30:
            summary_text = text
        else:
            summary_output = summarizer(text, max_length=min(len(text.split()), 150), min_length=30, do_sample=False)
            summary_text = summary_output[0]["summary_text"]

        _, past_summaries = get_recent_context()
        combined_summary = generate_combined_summary(summary_text, past_summaries)

        action_items = extract_action_items(text)
        save_meeting_record(summary=combined_summary, action_items=action_items)

        return JSONResponse(content={
            "type": "text",
            "transcript": text,
            "summary": [{
                "summary": combined_summary,
                "headline": "Combined Summary",
                "gist": "Main Idea",
                "start": 0,
                "end": 0
            }],
            "action_items": action_items
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Internal Server Error: {str(e)}"})

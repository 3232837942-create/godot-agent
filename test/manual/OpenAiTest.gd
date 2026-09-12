extends Node


@onready var chatButton: Button = $ChatRequest
@onready var chatStreamButton: Button = $ChatStreamRequest

const PROMPT := "Introduce godot-framework in one sentence."


func _ready() -> void:
	chatButton.pressed.connect(on_chat_pressed)
	chatStreamButton.pressed.connect(on_chat_stream_pressed)
	pass


func on_chat_pressed() -> void:
	var text := await OpenAiClient.async_chat(PROMPT)
	if StringUtils.is_blank(text):
		Log.error("OpenAI returned empty text")
		return
	Log.info("OpenAI reply:[{}]", text)
	pass


func on_chat_stream_pressed() -> void:
	var text := await OpenAiClient.async_chat_stream(PROMPT, "", func(delta: String) -> void:
		Log.info("OpenAI delta:[{}]", delta)
	)
	if StringUtils.is_blank(text):
		Log.error("OpenAI stream returned empty text")
		return
	Log.info("OpenAI stream reply:[{}]", text)
	pass

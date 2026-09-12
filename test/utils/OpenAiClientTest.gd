func consume_sse_buffer_test() -> void:
	var text := StringBuilder.new()
	var on_delta := func(delta: String) -> void:
		text.append_if_not_empty(delta)
		pass
	var remainder := OpenAiClient.consume_sse_buffer(
		"data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}]}\n",
		on_delta
	)
	assert(text.build_string() == "Hello")
	assert(remainder == StringUtils.EMPTY)
	pass


func consume_sse_buffer_partial_line_test() -> void:
	var text := StringBuilder.new()
	var on_delta := func(delta: String) -> void:
		text.append_if_not_empty(delta)
		pass
	var remainder := OpenAiClient.consume_sse_buffer("data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}", on_delta)
	assert(text.is_empty())
	assert(remainder.begins_with("data:"))
	var remainder2 := OpenAiClient.consume_sse_buffer(remainder + "\n", on_delta)
	assert(text.build_string() == "Hi")
	assert(remainder2 == StringUtils.EMPTY)
	pass


func parse_sse_text_test() -> void:
	var text := OpenAiClient.parse_sse_text("data: {\"choices\":[{\"delta\":{\"content\":\"Hel\"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}]}\n")
	assert(text == "Hello")
	pass


func extract_stream_delta_test() -> void:
	var delta := OpenAiClient.extract_stream_delta("{\"choices\":[{\"delta\":{\"role\":\"assistant\",\"content\":\"OK\"}}]}")
	assert(delta == "OK")
	pass


func extract_stream_delta_reasoning_test() -> void:
	var delta := OpenAiClient.extract_stream_delta("{\"choices\":[{\"delta\":{\"role\":\"assistant\",\"content\":null,\"reasoning_content\":\"think\"}}]}")
	assert(delta == "think")
	pass


func extract_stream_delta_whitespace_test() -> void:
	var delta := OpenAiClient.extract_stream_delta("{\"choices\":[{\"delta\":{\"content\":\" \"}}]}")
	assert(delta == " ")
	pass


func consume_sse_buffer_multichunk_test() -> void:
	var pending_build := StringBuilder.new()
	var text := StringBuilder.new()
	var on_delta := func(delta: String) -> void:
		text.append_if_not_empty(delta)
		pass
	var append_chunk := func(chunk_text: String) -> void:
		var buffer := pending_build.build_string() + chunk_text
		pending_build.clear()
		var remaining := OpenAiClient.consume_sse_buffer(buffer, on_delta)
		if StringUtils.is_not_empty(remaining):
			pending_build.append_if_not_empty(remaining)
		pass
	append_chunk.call("data: {\"choices\":[{\"delta\":{\"content\":\"Hel")
	append_chunk.call("lo\"}}]}\n\ndata: {\"choices\":[{\"delta\":{\"content\":\"!\"}}]}\n")
	assert(text.build_string() == "Hello!")
	pass

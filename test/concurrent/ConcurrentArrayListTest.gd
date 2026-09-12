var threadNum: int = 10
var count: int = 1_0000
var threads: Array[Thread] = []
var queue: ConcurrentArrayList = ConcurrentArrayList.new()

func ConcurrentArrayList_add_test() -> void:
	for i in threadNum:
		var thread := Thread.new()
		thread.start(Callable(self, "_add_thread"))
		threads.push_back(thread)
	for thread in threads:
		thread.wait_to_finish()
	pass

func ConcurrentArrayList_remove_test() -> void:
	threads.clear()
	for i in threadNum:
		var thread := Thread.new()
		thread.start(Callable(self, "_remove_thread"))
		threads.push_back(thread)
	for thread in threads:
		thread.wait_to_finish()
	pass

func ConcurrentArrayList_size_test() -> void:
	assert(queue.is_empty())
	pass

func _remove_thread() -> void:
	for i in count:
		if RandomUtils.random_boolean():
			queue.pop_front()
		else:
			queue.pop_back()
	pass

func _add_thread() -> void:
	for i in count:
		if queue.size() >= 0:
			queue.add(i)
	pass

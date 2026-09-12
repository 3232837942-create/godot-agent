func LazyCache_put_test() -> void:
	var lazyCache: LazyCache = LazyCache.new(10, 30 * TimeUtils.MILLIS_PER_MINUTE, 1 * TimeUtils.MILLIS_PER_SECOND)
	lazyCache.remove_listener = func(removes: Array[LazyCache.Cache], cause: LazyCache.RemovalCause) -> void:
		assert(removes.size() == 2)
		assert(cause == LazyCache.RemovalCause.SIZE)
		pass
	
	lazyCache.put(1, "a")
	lazyCache.put(2, "b")
	lazyCache.put(3, "c")
	lazyCache.put(4, "d")
	lazyCache.put(5, "e")
	lazyCache.put(6, "f")
	lazyCache.put(7, "g")
	lazyCache.put(8, "h")
	lazyCache.put(9, "i")
	lazyCache.put(10, "j")
	lazyCache.put(11, "k")
	lazyCache.put(12, "l")
	lazyCache.put(13, "m")
	lazyCache.put(14, "n")
	pass


func LazyCache_expire_test() -> void:
	var lazyCache: LazyCache = LazyCache.new(10, 3 * TimeUtils.MILLIS_PER_SECOND, 1 * TimeUtils.MILLIS_PER_SECOND)
	lazyCache.remove_listener = func(removes: Array[LazyCache.Cache], cause: LazyCache.RemovalCause) -> void:
		assert(removes.size() == 5)
		assert(cause == LazyCache.RemovalCause.EXPIRED)
		pass
	
	for i in 10:
		lazyCache.put(1, "a")
		lazyCache.put(2, "b")
		lazyCache.put(3, "c")
		lazyCache.put(4, "d")
		lazyCache.put(5, "e")
		var value = lazyCache.get_value(1)
		assert(value != null)
		await ThreadUtils.async_sleep(5 * TimeUtils.MILLIS_PER_SECOND)
		value = lazyCache.get_value(1)
		assert(value == null)
		assert(lazyCache.size() == 0)
	pass

func LazyCache_max_size_test() -> void:
	var lazyCache: LazyCache = LazyCache.new(3, 30 * TimeUtils.MILLIS_PER_MINUTE, 1 * TimeUtils.MILLIS_PER_SECOND)
	lazyCache.remove_listener = func(removes: Array[LazyCache.Cache], cause: LazyCache.RemovalCause) -> void:
		assert(removes.size() == 1)
		assert(cause == LazyCache.RemovalCause.SIZE)
		pass
	
	lazyCache.put(1, "a")
	await ThreadUtils.async_sleep(TimeUtils.MILLIS_PER_SECOND)
	lazyCache.put(2, "b")
	await ThreadUtils.async_sleep(TimeUtils.MILLIS_PER_SECOND)
	lazyCache.put(3, "c")
	await ThreadUtils.async_sleep(TimeUtils.MILLIS_PER_SECOND)
	lazyCache.put(4, "d")
	await ThreadUtils.async_sleep(TimeUtils.MILLIS_PER_SECOND)
	lazyCache.put(5, "e")
	pass

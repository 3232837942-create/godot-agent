## Locale label tests for GraphNodesConfig node definitions.


func graph_nodes_locale_test() -> void:
	assert(GuiLocale.node_label("input-audio") == GuiLocale.resolve("node.input-audio"))
	assert(GuiLocale.category_label(GraphNodesConfig.SOURCE_CATEGORY) == GuiLocale.resolve("category.source"))
	assert(
		GraphNodesConfig.get_def("input-audio").display_label()
		== GuiLocale.node_label("input-audio")
	)
	pass

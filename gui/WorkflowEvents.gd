class_name WorkflowEvents
extends RefCounted

static var events := Events.new()


class Events:
	signal step_started(node_id: String, label: String)
	signal step_finished(node_id: String, exit_code: int, output_path: String)
	signal pipeline_finished(success: bool, message: String)
	signal pipeline_stopped()
	pass

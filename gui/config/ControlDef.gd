class_name ControlDef
extends GraphNodeDef

var id: String = ""

# GraphNodeDef-Interface-Implement-Start
func catalog_id() -> String:
	return id


func is_batch() -> bool:
	return true
# GraphNodeDef-Interface-Implement-End
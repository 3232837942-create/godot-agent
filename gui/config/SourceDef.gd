class_name SourceDef
extends GraphNodeDef

var id: String = ""

# GraphNodeDef-Interface-Implement-Start
func catalog_id() -> String:
	return id


func is_source() -> bool:
	return true
# GraphNodeDef-Interface-Implement-End
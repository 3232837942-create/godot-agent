class_name SkillDef
extends GraphNodeDef

var skill: String = ""
var category: String = ""
var cli: String = ""

# GraphNodeDef-Interface-Implement-Start
func catalog_id() -> String:
	return skill
# GraphNodeDef-Interface-Implement-End
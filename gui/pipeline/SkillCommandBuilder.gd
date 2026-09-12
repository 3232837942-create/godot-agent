class_name SkillCommandBuilder
extends Object


static func build_argv(skill: SkillDef, resolved_inputs: Dictionary[String, String]) -> PackedStringArray:
	var argv := PackedStringArray()
	if skill.cli.is_empty():
		return argv

	var expanded := expand_cli(skill, resolved_inputs)
	if has_unexpanded_placeholders(expanded):
		Log.error(
			"cli has unexpanded placeholders skill:[{}] cli:[{}] inputs:[{}]",
			skill.catalog_id(),
			expanded,
			resolved_inputs,
		)
		return argv

	var parts := split_cli_args(expanded)
	if parts.is_empty():
		Log.error("cli expanded to empty argv for skill:[{}]", skill.catalog_id())
		return argv

	if not DependencyManifest.has_populated_runtime(parts[0]):
		Log.error("manifest entry not found for skill:[{}] runtime:[{}]", skill.catalog_id(), parts[0])
		return argv

	for part in parts:
		argv.append(resolve_repo_relative_path(part))
	return argv


static func resolve_repo_relative_path(part: String) -> String:
	var normalized := part.replace("\\", "/")
	if normalized.begins_with(".dependency/") or normalized.begins_with(".ai/"):
		return FileUtils.get_project_root_path().replace("\\", "/").path_join(normalized)
	return part


static func expand_cli(
	skill: SkillDef,
	resolved_inputs: Dictionary[String, String],
) -> String:
	var result := skill.cli
	for port in skill.inputs:
		result = result.replace(placeholder_for(port.id), resolved_inputs.get(port.id, ""))
	return result.strip_edges()


static func placeholder_for(port_id: String) -> String:
	return "{" + port_id + "}"


static func has_unexpanded_placeholders(text: String) -> bool:
	var start := text.find("{")
	while start >= 0:
		var end := text.find("}", start + 1)
		if end < 0:
			return false
		var token := text.substr(start, end - start + 1)
		if token.length() > 2:
			return true
		start = text.find("{", end + 1)
	return false


static func split_cli_args(line: String) -> PackedStringArray:
	var args := PackedStringArray()
	var current := ""
	var in_quote := false
	var quote_char := '"'

	for i in line.length():
		var c: String = line[i]
		if in_quote:
			if c == quote_char:
				in_quote = false
			else:
				current += c
		elif c == '"' or c == "'":
			in_quote = true
			quote_char = c
		elif c == " " or c == "\t":
			if not current.is_empty():
				args.append(current)
				current = ""
		else:
			current += c

	if not current.is_empty():
		args.append(current)

	return args

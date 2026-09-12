extends Node

@onready var sceneToMainButton: Button = $SceneToMain
@onready var addNodeButton: Button = $AddNode

func _ready() -> void:
	sceneToMainButton.pressed.connect(pressedSceneToMainButton)
	addNodeButton.pressed.connect(pressedSceneAddNodeButton)
	pass


func pressedSceneToMainButton():
	await SceneHelper.async_change_scene_to_file("test/manual/MyTestScene.tscn")
	#await SceneHelper.async_change_scene_to_file("zfoo/test/manual/MyTestScene.tscn", RectTransitionSlide.new())
	pass

func pressedSceneAddNodeButton():
	SceneHelper.add_scene_to_node(load("test/manual/MyTestScene.tscn"), gdf.gdf_node.get_tree().root)
	pass

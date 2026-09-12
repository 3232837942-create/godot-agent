class_name WorkflowDocument
extends RefCounted

const VERSION := 1

var version: int = VERSION
var name: String = "Untitled"
var nodes: Array[WorkflowNodeData] = []
var connections: Array[WorkflowConnection] = []

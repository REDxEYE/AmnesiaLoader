from UniLoader.common_api.xml_parsing import XmlAutoDeserialize, XChild, XAttr, parse_float_list, parse_bool


class Performance(XmlAutoDeserialize):
    cam_clip_panes: list[float] = XAttr("CamClipPlanes", deserializer=parse_float_list)
    lights_active: bool = XAttr("LightsActive", deserializer=parse_bool)
    ps_active: bool = XAttr("PSActive", deserializer=parse_bool)
    show_fog: bool = XAttr("ShowFog", deserializer=parse_bool)
    show_skybox: bool = XAttr("ShowSkybox", deserializer=parse_bool)
    world_reflection: bool = XAttr("WorldReflection", deserializer=parse_bool)


class Viewport(XmlAutoDeserialize):
    camera_position: list[float] = XAttr("CameraPosition", deserializer=parse_float_list)
    camera_target: list[float] = XAttr("CameraTarget", deserializer=parse_float_list)
    camera_zoom: float = XAttr("CameraZoom")
    grid_height: float = XAttr("GridHeight")
    grid_plane: int = XAttr("GridPlane")
    preset: int = XAttr("Preset")
    render_mode: int = XAttr("RenderMode")
    show_axes: bool = XAttr("ShowAxes")
    show_grid: bool = XAttr("ShowGrid")
    using_lt_cam: bool = XAttr("UsingLTCam")


class ViewportConfig(XmlAutoDeserialize):
    bg_color: list[float] = XAttr("BGColor", deserializer=parse_float_list)
    g_ambient_light: bool = XAttr("GAmbientLight")
    g_point_light: bool = XAttr("GPointLight")
    grid_snap: bool = XAttr("GridSnap")
    grid_snap_separation: float = XAttr("GridSnapSeparation")
    selected_viewport: int = XAttr("SelectedViewport")
    using_enlarged_viewport: bool = XAttr("UsingEnlargedViewport")
    viewports: list[Viewport] = XChild("Viewport")


class Group(XmlAutoDeserialize):
    id: int = XAttr("ID")
    name: str = XAttr("Name")
    visible: bool = XAttr("Visible", deserializer=parse_bool)


class Groups(XmlAutoDeserialize):
    groups: list[Group] = XChild("Group")


class EditorSession(XmlAutoDeserialize):
    performance: Performance = XChild("Performance")
    viewport_config: ViewportConfig = XChild("ViewportConfig")
    groups: Groups = XChild("Groups")

import pytest

from design_workbench.adapters.resources.catalog import Catalog
from design_workbench.domain.errors import WorkbenchError
from design_workbench.domain.models import BlockState, Cell, Point
from design_workbench.domain.placement import plan_placement


def place(
    catalog: Catalog,
    name: str,
    cells: dict[Point, Cell] | None = None,
    hit: Point = (0, -1, 0),
    normal: Point = (0, 1, 0),
    location: tuple[float, float, float] = (0.5, 1, 0.5),
    facing: str = "north",
    automatic: bool = True,
    properties: dict[str, str] | None = None,
) -> dict[Point, BlockState]:
    return dict(
        plan_placement(
            cells or {},
            BlockState.make(name, properties),
            hit,
            normal,
            location,
            facing,
            automatic,
            catalog,
        )
    )


@pytest.mark.parametrize(
    "name,wall",
    [
        ("torch", "wall_torch"),
        ("soul_torch", "soul_wall_torch"),
        ("redstone_torch", "redstone_wall_torch"),
        ("oak_sign", "oak_wall_sign"),
        ("white_banner", "white_wall_banner"),
        ("skeleton_skull", "skeleton_wall_skull"),
        ("player_head", "player_wall_head"),
    ],
)
def test_wall_variants_follow_clicked_face(catalog: Catalog, name: str, wall: str) -> None:
    cells = {(0, 0, 0): Cell(catalog.default("stone"))}
    before = dict(cells)
    result = place(catalog, name, cells, hit=(0, 0, 0), normal=(1, 0, 0))
    assert result[(1, 0, 0)].name == "minecraft:" + wall
    assert dict(result[(1, 0, 0)].properties)["facing"] == "east"
    assert cells == before
    floor = place(catalog, wall)
    assert floor[(0, 0, 0)].name == "minecraft:" + name


def test_wall_variant_preserves_shared_properties(catalog: Catalog) -> None:
    result = place(
        catalog,
        "redstone_torch",
        {(0, 0, 0): Cell(catalog.default("glass"))},
        hit=(0, 0, 0),
        normal=(0, 0, -1),
        properties={"lit": "false"},
    )
    assert dict(result[(0, 0, -1)].properties) == {"facing": "north", "lit": "false"}


def test_manual_direction_requires_its_actual_support(catalog: Catalog) -> None:
    cells = {(0, 0, 0): Cell(catalog.default("stone"))}
    with pytest.raises(WorkbenchError, match="支撑面"):
        place(
            catalog,
            "ladder",
            cells,
            hit=(0, 0, 0),
            normal=(1, 0, 0),
            automatic=False,
            properties={"facing": "north"},
        )
    result = place(catalog, "ladder", cells, hit=(0, 0, 0), normal=(1, 0, 0))
    assert dict(result[(1, 0, 0)].properties)["facing"] == "east"


def test_ladder_can_find_wall_when_clicking_floor(catalog: Catalog) -> None:
    cells = {(0, 0, -1): Cell(catalog.default("stone"))}
    result = place(catalog, "ladder", cells)
    assert dict(result[(0, 0, 0)].properties)["facing"] == "south"


@pytest.mark.parametrize("name", ["oak_button", "lever"])
@pytest.mark.parametrize(
    "normal,face", [((0, 1, 0), "floor"), ((0, -1, 0), "ceiling"), ((1, 0, 0), "wall")]
)
def test_button_and_lever_attachment(catalog: Catalog, name: str, normal: Point, face: str) -> None:
    result = place(
        catalog, name, {(0, 1, 0): Cell(catalog.default("stone"))}, hit=(0, 1, 0), normal=normal
    )
    assert dict(next(iter(result.values())).properties)["face"] == face


def test_lantern_and_hanging_sign_attach_below_support(catalog: Catalog) -> None:
    cells = {(0, 1, 0): Cell(catalog.default("stone"))}
    result = place(catalog, "lantern", cells, hit=(0, 1, 0), normal=(0, -1, 0))
    assert dict(result[(0, 0, 0)].properties)["hanging"] == "true"
    sign = place(catalog, "oak_wall_hanging_sign", cells, hit=(0, 1, 0), normal=(0, -1, 0))
    assert sign[(0, 0, 0)].name == "minecraft:oak_hanging_sign"
    with pytest.raises(WorkbenchError):
        place(catalog, "torch", cells, hit=(0, 1, 0), normal=(0, -1, 0))


def test_slab_click_fills_free_half_without_gap(catalog: Catalog) -> None:
    bottom = catalog.normalize(
        BlockState.make("stone_slab", {"type": "bottom", "waterlogged": "true"})
    )
    cells = {(0, 0, 0): Cell(bottom)}
    result = place(catalog, "stone_slab", cells, hit=(0, 0, 0), location=(0.5, 0.5, 0.5))
    assert list(result) == [(0, 0, 0)]
    assert dict(result[(0, 0, 0)].properties) == {"type": "double", "waterlogged": "false"}
    assert cells[(0, 0, 0)].state == bottom
    side = place(
        catalog, "stone_slab", cells, hit=(0, 0, 0), normal=(1, 0, 0), location=(1, 0.75, 0.5)
    )
    assert list(side) == [(0, 0, 0)]
    different = place(catalog, "oak_slab", cells, hit=(0, 0, 0))
    assert list(different) == [(0, 1, 0)]


def test_top_slab_bottom_click_merges_and_manual_preserves_half(catalog: Catalog) -> None:
    cells = {(0, 1, 0): Cell(catalog.normalize(BlockState.make("stone_slab", {"type": "top"})))}
    result = place(
        catalog, "stone_slab", cells, hit=(0, 1, 0), normal=(0, -1, 0), location=(0.5, 0.5, 0.5)
    )
    assert dict(result[(0, 1, 0)].properties)["type"] == "double"
    manual = place(catalog, "stone_slab", automatic=False, properties={"type": "top"})
    assert dict(manual[(0, 0, 0)].properties)["type"] == "top"


def test_slab_in_target_merges_only_complementary_half(catalog: Catalog) -> None:
    cells = {
        (0, 0, 0): Cell(catalog.default("stone")),
        (1, 0, 0): Cell(catalog.default("stone_slab")),
    }
    result = place(
        catalog, "stone_slab", cells, hit=(0, 0, 0), normal=(1, 0, 0), location=(1, 0.75, 0.5)
    )
    assert dict(result[(1, 0, 0)].properties)["type"] == "double"
    with pytest.raises(WorkbenchError) as error:
        place(
            catalog, "stone_slab", cells, hit=(0, 0, 0), normal=(1, 0, 0), location=(1, 0.25, 0.5)
        )
    assert error.value.code == "EDIT_COLLISION"


@pytest.mark.parametrize(
    "normal,height,half",
    [
        ((0, 1, 0), 1.0, "bottom"),
        ((0, -1, 0), 0.0, "top"),
        ((1, 0, 0), 0.75, "top"),
        ((1, 0, 0), 0.25, "bottom"),
    ],
)
def test_stairs_infer_half_and_view_direction(
    catalog: Catalog, normal: Point, height: float, half: str
) -> None:
    result = place(
        catalog,
        "andesite_stairs",
        hit=(0, 0, 0),
        normal=normal,
        location=(0.5, height, 0.5),
        facing="west",
        properties={"shape": "outer_left"},
    )
    properties = dict(next(iter(result.values())).properties)
    assert (properties["half"], properties["facing"], properties["shape"]) == (
        half,
        "west",
        "straight",
    )
    manual = place(
        catalog,
        "andesite_stairs",
        automatic=False,
        properties={"half": "top", "facing": "east", "shape": "outer_left"},
    )
    assert dict(manual[(0, 0, 0)].properties)["shape"] == "outer_left"


@pytest.mark.parametrize(
    "name",
    [
        "oak_door",
        "iron_door",
        "sunflower",
        "tall_grass",
        "pitcher_plant",
        "tall_seagrass",
        "small_dripleaf",
    ],
)
def test_tall_blocks_complete_and_reject_obstructed_partner(catalog: Catalog, name: str) -> None:
    result = place(catalog, name, properties={"half": "upper"})
    assert list(result) == [(0, 0, 0), (0, 1, 0)]
    assert dict(result[(0, 0, 0)].properties)["half"] == "lower"
    assert dict(result[(0, 1, 0)].properties)["half"] == "upper"
    cells = {(0, 1, 0): Cell(catalog.default("stone"))}
    before = dict(cells)
    with pytest.raises(WorkbenchError) as error:
        place(catalog, name, cells)
    assert error.value.code == "EDIT_COLLISION"
    assert cells == before


def test_bed_complete_with_shared_state_and_two_clear_positions(catalog: Catalog) -> None:
    result = place(catalog, "red_bed", facing="east", properties={"part": "head"})
    assert list(result) == [(0, 0, 0), (1, 0, 0)]
    assert dict(result[(1, 0, 0)].properties)["part"] == "head"
    assert dict(result[(0, 0, 0)].properties)["facing"] == "east"
    with pytest.raises(WorkbenchError) as error:
        place(catalog, "red_bed", {(1, 0, 0): Cell(catalog.default("stone"))}, facing="east")
    assert error.value.code == "EDIT_COLLISION"


def test_manual_upper_and_head_complete_correct_partner(catalog: Catalog) -> None:
    door = place(
        catalog,
        "oak_door",
        hit=(0, 2, 0),
        normal=(0, -1, 0),
        automatic=False,
        properties={"half": "upper", "hinge": "right"},
    )
    assert list(door) == [(0, 0, 0), (0, 1, 0)]
    assert all(dict(state.properties)["hinge"] == "right" for state in door.values())
    bed = place(catalog, "red_bed", automatic=False, properties={"part": "head", "facing": "east"})
    assert list(bed) == [(-1, 0, 0), (0, 0, 0)]


def test_adjacent_doors_get_complementary_hinges(catalog: Catalog) -> None:
    first = place(catalog, "oak_door", facing="north", location=(0.1, 1, 0.5))
    cells = {point: Cell(state) for point, state in first.items()}
    second = place(catalog, "oak_door", cells, hit=(1, -1, 0), facing="north")
    assert dict(first[(0, 0, 0)].properties)["hinge"] != dict(second[(1, 0, 0)].properties)["hinge"]


def test_axis_and_trapdoor_follow_face(catalog: Catalog) -> None:
    log = place(catalog, "oak_log", hit=(0, 0, 0), normal=(1, 0, 0))
    assert dict(log[(1, 0, 0)].properties)["axis"] == "x"
    trapdoor = place(
        catalog, "oak_trapdoor", hit=(0, 0, 0), normal=(0, 0, -1), location=(0.5, 0.8, 0)
    )
    assert dict(trapdoor[(0, 0, -1)].properties)["half"] == "top"
    assert dict(trapdoor[(0, 0, -1)].properties)["facing"] == "north"


def test_existing_blocks_never_overwritten(catalog: Catalog) -> None:
    cells = {(0, 0, 0): Cell(catalog.default("stone"))}
    with pytest.raises(WorkbenchError) as error:
        place(catalog, "dirt", cells)
    assert error.value.code == "EDIT_COLLISION"


@pytest.mark.parametrize(
    "normal,facing,location",
    [
        ((1, 1, 0), "north", (0.5, 0.5, 0.5)),
        ((0, 1, 0), "up", (0.5, 0.5, 0.5)),
        ((0, 1, 0), "north", (float("nan"), 0.5, 0.5)),
    ],
)
def test_invalid_hit_context_rejected(
    catalog: Catalog, normal: Point, facing: str, location: tuple[float, float, float]
) -> None:
    with pytest.raises(WorkbenchError) as error:
        place(catalog, "stone", normal=normal, facing=facing, location=location)
    assert error.value.code == "INVALID_PLACEMENT"


@pytest.mark.parametrize(
    "facing,rotation", [("north", "8"), ("east", "12"), ("south", "0"), ("west", "4")]
)
def test_floor_heads_face_player_with_correct_model_rotation(
    catalog: Catalog, facing: str, rotation: str
) -> None:
    head = place(catalog, "player_head", facing=facing)
    assert dict(head[(0, 0, 0)].properties)["rotation"] == rotation
    sign = place(catalog, "oak_sign", facing=facing)
    assert (int(dict(sign[(0, 0, 0)].properties)["rotation"]) + 8) % 16 == int(rotation)


@pytest.mark.parametrize("support", ["glass", "pumpkin", "melon", "stone", "oak_leaves"])
def test_full_transparent_and_connection_exception_blocks_support_wall_attachment(
    catalog: Catalog, support: str
) -> None:
    result = place(
        catalog,
        "ladder",
        {(0, 0, 0): Cell(catalog.default(support))},
        hit=(0, 0, 0),
        normal=(1, 0, 0),
    )
    assert dict(result[(1, 0, 0)].properties)["facing"] == "east"


@pytest.mark.parametrize("support", ["lantern", "chest", "dandelion", "iron_bars", "oak_fence"])
def test_partial_shapes_do_not_supply_full_wall_attachment(catalog: Catalog, support: str) -> None:
    with pytest.raises(WorkbenchError) as error:
        place(
            catalog,
            "ladder",
            {(0, 0, 0): Cell(catalog.default(support))},
            hit=(0, 0, 0),
            normal=(1, 0, 0),
        )
    assert error.value.code == "MISSING_SUPPORT"


@pytest.mark.parametrize("support", ["oak_fence", "cobblestone_wall", "iron_bars"])
@pytest.mark.parametrize("attachment", ["torch", "lantern", "oak_sign"])
def test_centered_attachments_can_stand_on_posts(
    catalog: Catalog, support: str, attachment: str
) -> None:
    result = place(catalog, attachment, {(0, 0, 0): Cell(catalog.default(support))}, hit=(0, 0, 0))
    assert (0, 1, 0) in result


def test_lantern_can_hang_below_fence_post(catalog: Catalog) -> None:
    result = place(
        catalog,
        "lantern",
        {(0, 1, 0): Cell(catalog.default("oak_fence"))},
        hit=(0, 1, 0),
        normal=(0, -1, 0),
    )
    assert dict(result[(0, 0, 0)].properties)["hanging"] == "true"


@pytest.mark.parametrize("age,parts", [("0", 1), ("2", 1), ("3", 2), ("4", 2)])
def test_pitcher_crop_only_completes_upper_part_when_mature(
    catalog: Catalog, age: str, parts: int
) -> None:
    result = place(catalog, "pitcher_crop", properties={"age": age})
    assert len(result) == parts
    if parts == 2:
        assert dict(result[(0, 1, 0)].properties)["half"] == "upper"
        assert dict(result[(0, 1, 0)].properties)["age"] == age


@pytest.mark.parametrize(
    "normal,face", [((0, 1, 0), "floor"), ((0, -1, 0), "ceiling"), ((1, 0, 0), "wall")]
)
def test_grindstone_follows_attachment_face(catalog: Catalog, normal: Point, face: str) -> None:
    result = place(
        catalog,
        "grindstone",
        {(0, 1, 0): Cell(catalog.default("stone"))},
        hit=(0, 1, 0),
        normal=normal,
    )
    assert dict(next(iter(result.values())).properties)["face"] == face


@pytest.mark.parametrize(
    "normal,attachment", [((0, 1, 0), "floor"), ((0, -1, 0), "ceiling"), ((1, 0, 0), "single_wall")]
)
def test_bell_follows_attachment_face(catalog: Catalog, normal: Point, attachment: str) -> None:
    result = place(
        catalog, "bell", {(0, 1, 0): Cell(catalog.default("stone"))}, hit=(0, 1, 0), normal=normal
    )
    assert dict(next(iter(result.values())).properties)["attachment"] == attachment


def test_bell_between_walls_uses_both_supports(catalog: Catalog) -> None:
    cells = {(0, 0, 0): Cell(catalog.default("stone")), (2, 0, 0): Cell(catalog.default("stone"))}
    result = place(catalog, "bell", cells, hit=(0, 0, 0), normal=(1, 0, 0))
    assert dict(result[(1, 0, 0)].properties)["attachment"] == "double_wall"


@pytest.mark.parametrize("name", ["vine", "glow_lichen", "sculk_vein"])
def test_multiface_attachments_choose_the_clicked_support(catalog: Catalog, name: str) -> None:
    result = place(
        catalog, name, {(0, 0, 0): Cell(catalog.default("stone"))}, hit=(0, 0, 0), normal=(1, 0, 0)
    )
    properties = dict(result[(1, 0, 0)].properties)
    assert properties["west"] == "true"
    assert all(properties[key] == "false" for key in ("north", "east", "south", "up"))


def test_wall_corals_switch_to_floor_and_tripwire_hook_faces_out(catalog: Catalog) -> None:
    cells = {(0, 0, 0): Cell(catalog.default("stone"))}
    coral = place(catalog, "tube_coral_fan", cells, hit=(0, 0, 0), normal=(1, 0, 0))
    assert coral[(1, 0, 0)].name == "minecraft:tube_coral_wall_fan"
    assert dict(coral[(1, 0, 0)].properties)["facing"] == "east"
    floor = place(catalog, "tube_coral_wall_fan")
    assert floor[(0, 0, 0)].name == "minecraft:tube_coral_fan"
    hook = place(catalog, "tripwire_hook", cells, hit=(0, 0, 0), normal=(1, 0, 0))
    assert dict(hook[(1, 0, 0)].properties)["facing"] == "east"
    with pytest.raises(WorkbenchError):
        place(catalog, "tripwire_hook")


@pytest.mark.parametrize(
    "normal,facing",
    [((1, 0, 0), "west"), ((0, 0, -1), "south"), ((0, 1, 0), "down"), ((0, -1, 0), "down")],
)
def test_hopper_output_targets_the_clicked_block(
    catalog: Catalog, normal: Point, facing: str
) -> None:
    result = place(catalog, "hopper", hit=(0, 0, 0), normal=normal)
    assert dict(next(iter(result.values())).properties)["facing"] == facing


@pytest.mark.parametrize(
    "name,properties,support",
    [
        ("torch", {}, (0, -1, 0)),
        ("lantern", {"hanging": "true"}, (0, 1, 0)),
        ("oak_hanging_sign", {}, (0, 1, 0)),
        ("ladder", {"facing": "east"}, (-1, 0, 0)),
        ("oak_button", {"face": "ceiling"}, (0, 1, 0)),
        ("grindstone", {"face": "floor"}, (0, -1, 0)),
        ("bell", {"attachment": "single_wall", "facing": "south"}, (0, 0, -1)),
        ("glow_lichen", {"west": "true"}, (-1, 0, 0)),
        ("oak_door", {"half": "upper"}, (0, -2, 0)),
    ],
)
def test_support_inspection_uses_placement_rules_without_mutation(
    catalog: Catalog, name: str, properties: dict[str, str], support: Point
) -> None:
    from design_workbench.domain.placement import missing_supports

    state = catalog.normalize(BlockState.make(name, properties))
    # Work at y=10 so a removed support cannot be confused with virtual ground.
    point = (0, 10, 0)
    support_point = (support[0], support[1] + 10, support[2])
    cells = {support_point: Cell(catalog.default("stone")), point: Cell(state)}
    before = dict(cells)
    assert missing_supports(cells, point, state, catalog) == []
    assert cells == before
    del cells[support_point]
    assert missing_supports(cells, point, state, catalog) == [support_point]
    cells[support_point] = Cell(catalog.default("torch"))
    assert missing_supports(cells, point, state, catalog) == [support_point]


@pytest.mark.parametrize("facing,axis", [("north", "x"), ("east", "z")])
def test_portal_axis_stays_horizontal(catalog: Catalog, facing: str, axis: str) -> None:
    result = place(catalog, "nether_portal", facing=facing)
    assert dict(result[(0, 0, 0)].properties)["axis"] == axis


def test_registry_default_materials_never_produce_invalid_placement_states(
    catalog: Catalog,
) -> None:
    for name in catalog.blocks:
        try:
            place(catalog, name)
        except WorkbenchError as error:
            assert error.code in {"MISSING_SUPPORT", "INVALID_PLACEMENT"}, name


@pytest.mark.parametrize("version", ["1.21.11", "26.1"])
def test_new_copper_attachment_families(version: str) -> None:
    catalog = Catalog(version)
    cells = {(0, 1, 0): Cell(catalog.default("stone"))}
    torch = place(catalog, "copper_torch", cells, hit=(0, 1, 0), normal=(1, 0, 0))
    assert torch[(1, 1, 0)].name == "minecraft:copper_wall_torch"
    assert dict(torch[(1, 1, 0)].properties)["facing"] == "east"
    for name in catalog.blocks:
        if name.endswith("copper_lantern"):
            result = place(catalog, name, cells, hit=(0, 1, 0), normal=(0, -1, 0))
            assert dict(result[(0, 0, 0)].properties)["hanging"] == "true", name


@pytest.mark.parametrize("version", Catalog.versions())
def test_all_registry_materials_produce_valid_states_on_supported_faces(version: str) -> None:
    catalog = Catalog(version)
    cells = {(0, 10, 0): Cell(catalog.default("stone"))}
    for name in catalog.blocks:
        for normal in ((0, 1, 0), (1, 0, 0), (0, -1, 0)):
            try:
                place(catalog, name, cells, hit=(0, 10, 0), normal=normal, location=(0.5, 0.5, 0.5))
            except WorkbenchError as error:
                assert error.code in {"MISSING_SUPPORT", "INVALID_PLACEMENT"}, (
                    version,
                    name,
                    normal,
                )

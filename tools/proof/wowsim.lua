-- wowproof's adapter (unit-frames' wowproof/README.md "Adapter contract") over the simulated client's widgets
-- (tools/tests/wowsim.lua: each widget's state in Sim.state). Loaded by tools/proof.py in the sim's Lua:
-- dofile(path)(Sim, options) -> the adapter. options.skip(region): true for a region (and all under it) left
-- out of the picture (the map's ground: the tiles are the client's own art, which a render can't have).

return function(Sim, options)
	options = options or {}
	local S = Sim.state
	local skip = options.skip or function() return false end

	-- The client's font objects' colours (FontStyles.xml: Normal gold, Highlight white), by object.
	local GOLD, WHITE = { 1, 0.82, 0, 1 }, { 1, 1, 1, 1 }
	local fontColor = {}
	for name, color in pairs({ GameFontNormal = GOLD, GameFontNormalSmall = GOLD, GameFontNormalLarge = GOLD,
		GameFontHighlight = WHITE, GameFontHighlightSmall = WHITE }) do
		if _G[name] then fontColor[_G[name]] = color end
	end

	local function Plain(c)
		if not c then return nil end
		if c.GetRGBA then return { c:GetRGBA() } end
		return { c[1], c[2], c[3], c[4] or 1 }
	end

	local a = {}

	function a.Parent(r) return S[r].parent end

	function a.Children(r)
		local st, out = S[r], {}
		for _, c in ipairs(st.children or {}) do
			if not skip(c) then out[#out + 1] = c end
		end
		for _, c in ipairs(st.regions or {}) do
			if not skip(c) then out[#out + 1] = c end
		end
		table.sort(out, function(x, y) return S[x].order < S[y].order end)
		return out
	end

	function a.Order(r) return S[r].order end
	function a.Type(r) return S[r].type end
	function a.Name(r) return S[r].name end

	function a.Points(r)
		local out = {}
		for _, p in ipairs(S[r].points) do
			out[#out + 1] = { point = p.point, relativeTo = p.rel, relativePoint = p.relPoint, x = p.x, y = p.y }
		end
		return out
	end

	function a.Size(r)
		local st = S[r]
		return st.width or 0, st.height or 0
	end

	function a.Scale(r) return S[r].scale or 1 end
	-- A button's own textures as the client shows them, the mouse elsewhere: the highlight only while locked, the
	-- pushed and disabled ones never (the sim keeps the disabled one under the key its disabled flag uses). The
	-- sim keeps them all shown (tools/tests/wowsim.lua's buttonTexture).
	local function ButtonShows(r, b)
		if b.highlight == r then return b.lit == true end
		if b.pushed == r or b.disabled == r then return false end
		return true
	end
	function a.Shown(r)
		local st = S[r]
		if st.shown == false then return false end
		local b = st.parent and S[st.parent]
		return not b or ButtonShows(r, b)
	end
	function a.Alpha(r) return S[r].alpha or 1 end
	function a.IgnoresParentAlpha(r) return S[r].ignoreParentAlpha == true end
	function a.Strata(r)
		local st = S[r]
		return st.strataSet and st.strata or nil
	end
	function a.Level(r) return S[r].level or 0 end
	function a.Layer(r) return S[r].layer, S[r].sublevel end
	-- A ScrollFrame always cuts its scroll child to its rect in the client; others only with SetClipsChildren.
	function a.ClipsChildren(r) return S[r].clips == true or S[r].type == "ScrollFrame" end

	function a.Texture(r)
		local st = S[r]
		local g = st.gradient
		local file = st.texture
		if file ~= nil then file = tostring(file) end
		local atlas, coords = st.atlas, st.texCoord and { unpack(st.texCoord) } or nil
		local pseudo = file and file:match("^atlas/(.+)$")
		if pseudo and not atlas then
			atlas, file = pseudo, nil
			local whole = coords and coords[1] == 0 and coords[2] == 1 and coords[3] == 0 and coords[4] == 1
			if whole then coords = nil end
		end
		return {
			color = Plain(st.color),
			vertexColor = Plain(st.vertex),
			file = file,
			atlas = atlas,
			gradient = g and { orientation = g[1], from = Plain(g[2]), to = Plain(g[3]) } or nil,
			blend = st.blend,
			texCoords = coords,
		}
	end

	function a.Bar() return nil end

	function a.Text(r)
		local st = S[r]
		if st.type ~= "FontString" then return nil end
		local font, size, flags
		if st.font then
			font, size, flags = st.font[1], st.font[2], st.font[3]
		elseif st.fontObject and st.fontObject.GetFont then
			font, size, flags = st.fontObject:GetFont()
		end
		local color = st.textRGBA or fontColor[st.fontObject] or WHITE
		return { text = st.text, font = font, size = size or 12, flags = flags, color = { unpack(color) },
			justifyH = st.justifyH, justifyV = st.justifyV }
	end

	return a
end

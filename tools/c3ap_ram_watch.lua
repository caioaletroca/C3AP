-- C3AP RAM watch for BizHawk (PSX, NTSC-U SCUS-94244). Run it WITHOUT the Archipelago client.
-- Tools > Lua Console > open this script. It draws the values the client relies on and logs every change with the
-- frame number, so you can play through the tests in tools/VERIFY.md and paste the console log back.
--
-- Bit fields (CRYSTALS, GEMS, POWERS) are logged as "bitN->1": N is the bit number the client uses.
--
-- Keys, checked against BizHawk's config (taken: F frame advance, I quick save, P quick load, Q read-only,
-- X/Z RetroAchievements, W/A/S/D/E/Q/K the controller):
--   U  snapshot the GOOL globals block and what follows it (relics, flags)
--   L  list every word there that changed since the U snapshot
--   G  "last level" probe: arm, finish a level normally, wait in the warp room (see the function)
--   O  +5 crystals: the next warp room's five levels (room 1 first). Powers untouched.
--   B  HOLD powers at 0 every frame (as the client would); press again to release
--   C  HOLD all powers on (0x3F, the cheat code's value) every frame; press again to release
--   Y  shuffle test: once = Toad Village loads Under Pressure, twice = Future Frenzy (cross room), 3x = off
--   H  mark Tiny, Dingodile, N. Tropy and N. Gin as beaten (boss field bits 6, 3, 4, 5) and reload the hub
--   J  all five colored gems on / back to what you had (written once, so the game can still add gems)
--   R  reload the warp room (asks the loader for scene 02, like the client could)
--   N  +1 life      M  +1 Aku Aku mask      (press in the warp room, then enter a level)
--   T  relic test on/off: Under Pressure gets both its sapphire and gold bits (is that platinum?)
--   V  +5 sapphire relics per press (next five main levels), for the secret warp room test

memory.usememorydomain("MainRAM")

local GLOBALS_START = 0x068EF8
local GLOBALS_END = 0x06917C          -- POWERS + 4
local SCAN_END = 0x069400             -- U / L also cover what follows (sapphires sit at 0x0691B4)
local LEVEL = 0x068EF8
local RESPAWN = 0x068F0C              -- guess: Crash 1's index 5
local GAMESTATE = 0x068F3C            -- guess: Crash 1's index 17
local LIVES = 0x068F58
local HEALTH = 0x068F5C
local FRUIT = 0x068F60                -- guess: Crash 1's index 26
local GEMS, GEMS_SIZE = 0x068FB0, 8
local CRYSTALS, CRYSTALS_SIZE = 0x06912C, 6
local POWERS = 0x069178
local SCENE_ID = 0x060ABC
local SCENE_REQUEST = 0x060AC0

local TOAD_VILLAGE, UNDER_PRESSURE = 0x0B, 0x0E

local WORDS = {
  {"CAND F64", 0x068F64, 0},
  {"CAND 010", 0x069010, 0},
  {"CAND 1F0", 0x0691F0, 0},
  {"LEVEL>>8", LEVEL, 8},
  {"RESPAWN?", RESPAWN, 0},
  {"GAMESTATE?", GAMESTATE, 0},
  {"LIVES", LIVES, 0},
  {"HEALTH", HEALTH, 0},
  {"FRUIT?", FRUIT, 0},
  {"POWERS", POWERS, 0},
  {"SCENE_ID", SCENE_ID, 0},
  {"SCENE_REQ", SCENE_REQUEST, 0},
}

local FIELDS = {
  {"CRYSTALS", CRYSTALS, CRYSTALS_SIZE},
  {"GEMS", GEMS, GEMS_SIZE},
}

local function log(text) console.log(string.format("[%d] %s", emu.framecount(), text)) end

local function read_field(addr, size)
  return memory.read_bytes_as_array(addr, size)   -- 1-indexed bytes, little endian
end

local function field_hex(bytes)
  local s = ""
  for i = #bytes, 1, -1 do s = s .. string.format("%02X", bytes[i]) end
  return s
end

local function bit_changes(old, new)
  local changed = ""
  for i = 1, #new do
    local diff = old[i] ~ new[i]
    for b = 0, 7 do
      if (diff >> b) & 1 == 1 then
        changed = changed .. string.format(" bit%d->%d", (i - 1) * 8 + b, (new[i] >> b) & 1)
      end
    end
  end
  return changed
end

local function word_bit_changes(old, new)
  local changed, diff = "", old ~ new
  for b = 0, 31 do
    if (diff >> b) & 1 == 1 then changed = changed .. string.format(" bit%d->%d", b, (new >> b) & 1) end
  end
  return changed
end

-- U / L: globals block snapshot and diff
local snapshot = nil
local function take_snapshot()
  snapshot = {}
  for addr = GLOBALS_START, SCAN_END - 4, 4 do snapshot[addr] = memory.read_u32_le(addr) end
  log("globals snapshot taken")
end

local function diff_snapshot()
  if snapshot == nil then log("press U first") return end
  local n = 0
  for addr = GLOBALS_START, SCAN_END - 4, 4 do
    local value = memory.read_u32_le(addr)
    if value ~= snapshot[addr] then
      n = n + 1
      console.log(string.format("  0x%08X (index %d)  %08X -> %08X", 0x80000000 + addr, (addr - GLOBALS_START) // 4,
        snapshot[addr], value))
    end
  end
  log(string.format("%d globals changed since the snapshot", n))
end

-- G: disc ID search
local function find_disc_id()
  local size = 0x20000
  local data = memory.read_bytes_as_array(0, size)
  local markers = {"SCUS_942.44", "SCUS-94244"}
  local found = 0
  for _, marker in ipairs(markers) do
    local first = marker:byte(1)
    for i = 1, size - #marker + 1 do
      if data[i] == first then
        local ok = true
        for j = 2, #marker do
          if data[i + j - 1] ~= marker:byte(j) then ok = false break end
        end
        if ok then
          found = found + 1
          log(string.format("disc ID %s at MainRAM 0x%06X", marker, i - 1))
        end
      end
    end
  end
  if found == 0 then log("disc ID not found in the first 128 KB") end
end

-- O: the crystals of one more warp room (bit = level ID, as Toad Village's bit 11)
local ROOM_LEVELS = {
  {0x0B, 0x0E, 0x0A, 0x0C, 0x19},
  {0x0F, 0x16, 0x15, 0x12, 0x11},
  {0x10, 0x1C, 0x1A, 0x14, 0x1D},
  {0x1E, 0x13, 0x0D, 0x1B, 0x18},
  {0x23, 0x20, 0x22, 0x17, 0x24},
}
local function crystal_count()
  local n = 0
  for _, b in ipairs(memory.read_bytes_as_array(CRYSTALS, CRYSTALS_SIZE)) do
    while b > 0 do n = n + (b & 1) b = b >> 1 end
  end
  return n
end
local function open_everything()
  for room, lids in ipairs(ROOM_LEVELS) do
    local missing = false
    for _, lid in ipairs(lids) do
      if memory.read_u8(CRYSTALS + lid // 8) & (1 << (lid % 8)) == 0 then missing = true end
    end
    if missing then
      for _, lid in ipairs(lids) do
        local addr = CRYSTALS + lid // 8
        memory.write_u8(addr, memory.read_u8(addr) | (1 << (lid % 8)))
      end
      log(string.format("poke O: warp room %d crystals set, %d crystals total", room, crystal_count()))
      return
    end
  end
  log(string.format("poke O: all 25 already set (%d total)", crystal_count()))
end

-- B: hold powers at 0 every frame (like the client will) until pressed again
local holds = {}   -- addr -> value written every frame
local held_was = {} -- addr -> value before the hold, put back on release
local function toggle_hold(addr, value, key, what)
  if holds[addr] == nil then
    held_was[addr] = memory.read_u32_le(addr)
    holds[addr] = value
    log(string.format("poke %s: HOLD %s (0x%08X) at %08X, was %08X; press %s again to release", key, what,
      0x80000000 + addr, value, held_was[addr], key))
  else
    holds[addr] = nil
    memory.write_u32_le(addr, held_was[addr])
    log(string.format("poke %s: released %s (0x%08X), put back %08X", key, what, 0x80000000 + addr, held_was[addr]))
  end
end
local function toggle_powers() toggle_hold(POWERS, 0, "B", "powers") end

-- Y: level shuffle test. Press once: same room (Under Pressure). Twice: cross room (Future Frenzy). Three times: off.
local FUTURE_FRENZY = 0x1B
local redirect_target = nil
local function toggle_redirect()
  if redirect_target == nil then
    redirect_target = UNDER_PRESSURE
    log("shuffle test ARMED: Toad Village's button should load Under Pressure (same room)")
  elseif redirect_target == UNDER_PRESSURE then
    redirect_target = FUTURE_FRENZY
    log("shuffle test ARMED: Toad Village's button should load Future Frenzy (warp room 4)")
  else
    redirect_target = nil
    log("shuffle test off")
  end
end

-- G: "last level" probe. The warp room spawns Crash at the last level's button (R shows it). A normal finish seems to
-- set that value to the level just finished. Arm with G, finish a level normally, wait in the warp room: the probe
-- lists the words that changed and the ones holding the finished level's ID.
local PROBE_END = 0x069400
local probe = nil   -- {state = "armed" | "exited", snap = {}, lid = n, frames = n}
local function words_now()
  local t = {}
  for addr = GLOBALS_START, PROBE_END - 4, 4 do t[addr] = memory.read_u32_le(addr) end
  return t
end
local function is_lid(value, lid) return value == lid or value == (lid << 8) end
local function toggle_probe()
  if probe == nil then
    probe = {state = "armed"}
    log("probe G ARMED: finish a level normally, then stand still in the warp room for ~10 seconds")
  else
    probe = nil
    log("probe G off")
  end
end
local function run_probe()
  if probe == nil then return end
  local state = memory.read_u32_le(GAMESTATE)
  if probe.state == "armed" and state == 0x300 then
    probe.state, probe.snap, probe.lid, probe.frames = "exited", words_now(), memory.read_u32_le(LEVEL) >> 8, 0
    probe.button = memory.read_u32_le(0x0691F0) >> 8
    log(string.format("probe G: normal finish of level %02X (button candidate 1F0 = %02X). Words holding %02X now:",
      probe.lid, probe.button, probe.lid))
    for addr, value in pairs(probe.snap) do
      if is_lid(value, probe.lid) then log(string.format("  0x%08X = %08X", 0x80000000 + addr, value)) end
    end
  elseif probe.state == "exited" then
    if (memory.read_u32_le(LEVEL) >> 8) == 2 and state == 0x100 then probe.frames = probe.frames + 1 end
    if probe.frames == 400 then
      local now = words_now()
      log(string.format("probe G: back in the warp room. Changed words (* = holds the finished level %02X, " ..
        "B = held the button's level %02X before):", probe.lid, probe.button))
      local n = 0
      for addr = GLOBALS_START, PROBE_END - 4, 4 do
        if now[addr] ~= probe.snap[addr] then
          n = n + 1
          local mark = (is_lid(now[addr], probe.lid) and "*" or " ") .. (is_lid(probe.snap[addr], probe.button) and "B" or " ")
          log(string.format("  %s 0x%08X  %08X -> %08X", mark, 0x80000000 + addr, probe.snap[addr], now[addr]))
        end
      end
      log(string.format("probe G: %d words changed. Also holding %02X now:", n, probe.lid))
      for addr = GLOBALS_START, PROBE_END - 4, 4 do
        if is_lid(now[addr], probe.lid) then log(string.format("  0x%08X = %08X", 0x80000000 + addr, now[addr])) end
      end
      probe = nil
    end
  end
end

local function add_unit(addr, name)
  memory.write_u32_le(addr, memory.read_u32_le(addr) + 0x100)
  log(string.format("poke: %s +1 (now %08X)", name, memory.read_u32_le(addr)))
end

local gem_test_saved = nil   -- colored gem bits before J
local relic_test_on = false

local actions = {
  U = take_snapshot,
  L = diff_snapshot,
  G = toggle_probe,
  O = open_everything,
  B = toggle_powers,
  C = function() toggle_hold(POWERS, 0x3F, "C", "all powers") end,
  Y = toggle_redirect,
  N = function() add_unit(LIVES, "lives") end,
  H = function()
    local was = memory.read_u32_le(0x068F64)
    memory.write_u32_le(0x068F64, was | 0x78)
    memory.write_u32_le(SCENE_REQUEST, 0x02)
    log(string.format("poke H: boss field %08X -> %08X (4 bosses beaten), reloading the hub", was, was | 0x78))
  end,
  J = function()
    local addr = GEMS + 7               -- bits 56-63: Red 58, Green 59, Purple 60, Blue 61, Yellow 62
    local now = memory.read_u8(addr)
    if gem_test_saved == nil then
      gem_test_saved = now & 0x7C
      memory.write_u8(addr, now | 0x7C)
      log("poke J: all five colored gems ON (gem paths open on the next level load); press J again for off")
    else
      memory.write_u8(addr, (now & ~0x7C) | gem_test_saved)
      log("poke J: colored gems back to what you had")
      gem_test_saved = nil
    end
  end,
  R = function()
    memory.write_u32_le(SCENE_REQUEST, 0x02)
    log("poke R: scene request 02 (reload the warp room)")
  end,
  T = function()
    -- platinum = sapphire bit AND gold bit? Toggle Under Pressure (bit 14) in both fields at once.
    local SAPPHIRE, GOLD = 0x0691B4, 0x0691BC
    if not relic_test_on then
      memory.write_u32_le(SAPPHIRE, memory.read_u32_le(SAPPHIRE) | (1 << 14))
      memory.write_u32_le(GOLD, memory.read_u32_le(GOLD) | (1 << 14))
      log("poke T: Under Pressure sapphire+gold bits ON -- platinum showing?")
    else
      memory.write_u32_le(SAPPHIRE, memory.read_u32_le(SAPPHIRE) & ~(1 << 14))
      memory.write_u32_le(GOLD, memory.read_u32_le(GOLD) & ~(1 << 14))
      log("poke T: Under Pressure test bits OFF")
    end
    relic_test_on = not relic_test_on
  end,
  V = function()
    -- +5 sapphire relics (the next five main levels without one), for the secret warp room test
    local SAPPHIRE = 0x0691B4
    local added = 0
    for _, lids in ipairs(ROOM_LEVELS) do
      for _, lid in ipairs(lids) do
        local addr = SAPPHIRE + lid // 8
        if added < 5 and memory.read_u8(addr) & (1 << (lid % 8)) == 0 then
          memory.write_u8(addr, memory.read_u8(addr) | (1 << (lid % 8)))
          added = added + 1
        end
      end
    end
    local n = 0
    for _, b in ipairs(memory.read_bytes_as_array(SAPPHIRE, 16)) do
      while b > 0 do n = n + (b & 1) b = b >> 1 end
    end
    log(string.format("poke V: +%d sapphire relics, %d relic bits set (sapphire + gold fields)", added, n))
  end,
  M = function() add_unit(HEALTH, "masks") end,
}

local last_word, last_field, held = {}, {}, {}
log("C3AP RAM watch ready (U/L globals diff, G last-level probe, O crystals, B no powers, C all powers, T relic test, V +5 relics, H bosses, J gems on/off, R reload hub, Y shuffle, N life, M mask)")

while true do
  local keys = input.get()
  for key, action in pairs(actions) do
    if keys[key] and not held[key] then action() end
    held[key] = keys[key] == true
  end

  for addr, value in pairs(holds) do memory.write_u32_le(addr, value) end
  run_probe()

  -- Shuffle test: swap the button's request the frame it appears, or ask again once Toad Village has loaded.
  if redirect_target ~= nil then
    local request = memory.read_u32_le(SCENE_REQUEST)
    if request == TOAD_VILLAGE then
      memory.write_u32_le(SCENE_REQUEST, redirect_target)
      log(string.format("shuffle test: caught request 0B, swapped to %02X", redirect_target))
      redirect_target = nil
    elseif request == 0xFFFFFFFF and (memory.read_u32_le(LEVEL) >> 8) == TOAD_VILLAGE then
      memory.write_u32_le(SCENE_REQUEST, redirect_target)
      log(string.format("shuffle test: missed the request, Toad Village loaded; asked for %02X", redirect_target))
      redirect_target = nil
    end
  end

  local y = 10
  for _, w in ipairs(WORDS) do
    local name, addr, shift = w[1], w[2], w[3]
    local value = memory.read_u32_le(addr)
    gui.text(10, y, string.format("%-11s %08X", name, shift > 0 and (value >> shift) or value))
    y = y + 14
    if last_word[name] ~= nil and last_word[name] ~= value then
      local extra = name == "POWERS" and word_bit_changes(last_word[name], value) or ""
      log(string.format("%s %08X -> %08X%s", name, last_word[name], value, extra))
    end
    last_word[name] = value
  end
  for _, f in ipairs(FIELDS) do
    local name, addr, size = f[1], f[2], f[3]
    local bytes = read_field(addr, size)
    gui.text(10, y, string.format("%-11s %s", name, field_hex(bytes)))
    y = y + 14
    if last_field[name] ~= nil then
      local changes = bit_changes(last_field[name], bytes)
      if changes ~= "" then
        log(string.format("%s %s -> %s%s", name, field_hex(last_field[name]), field_hex(bytes), changes))
      end
    end
    last_field[name] = bytes
  end
  emu.frameadvance()
end

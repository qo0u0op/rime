-- Select a character from the current phrase with < and >.
-- Source: https://github.com/BlindingDark/rime-lua-select-character
-- License: LGPL-3.0
--
-- http://lua-users.org/lists/lua-l/2014-04/msg00590.html
local function utf8_sub(s, i, j)
   i = i or 1
   j = j or -1

   if i < 1 or j < 1 then
      local n = utf8.len(s)
      if not n then return nil end
      if i < 0 then i = n + 1 + i end
      if j < 0 then j = n + 1 + j end
      if i < 0 then i = 1 elseif i > n then i = n end
      if j < 0 then j = 1 elseif j > n then j = n end
   end

   if j < i then return "" end

   i = utf8.offset(s, i)
   j = utf8.offset(s, j + 1)

   if i and j then
      return s:sub(i, j - 1)
   elseif i then
      return s:sub(i)
   else
      return ""
   end
end

local function first_character(s)
   return utf8_sub(s, 1, 1)
end

local function last_character(s)
   return utf8_sub(s, -1, -1)
end

local function get_commit_text(context, fun)
   local candidate_text = context:get_selected_candidate().text
   local selected_character = fun(candidate_text)

   context:clear_previous_segment()
   local commit_text = context:get_commit_text()

   context:clear()

   return commit_text .. selected_character
end

local function key_matches(key, configured)
   local repr = key:repr()
   if repr == configured then
      return true
   end

   -- fcitx5 may report shifted keys either as "Shift+less"/"Shift+greater"
   -- or as "Shift+comma"/"Shift+period"; accept both forms without stealing
   -- the plain comma/period keys.
   local mods, base = repr:match('^(.*)%+([^+]+)$')
   if not base then
      base = repr
      mods = ''
   end
   if base == configured then
      return true
   end
   if mods:find('Shift', 1, true) then
      local alias = {
         comma = 'less',
         period = 'greater',
         less = 'comma',
         greater = 'period',
         bracketleft = 'braceleft',
         bracketright = 'braceright',
         braceleft = 'bracketleft',
         braceright = 'bracketright',
      }
      if alias[base] == configured then
         return true
      end
   end
   return false
end

local function select_character(key, env)
   local engine = env.engine
   local context = engine.context
   local config = engine.schema.config

   local first_key = config:get_string('key_binder/select_first_character') or 'less'
   local last_key = config:get_string('key_binder/select_last_character') or 'greater'

   local commit_text = context:get_commit_text()
   local selected = context:get_selected_candidate()
   local selected_len = selected and selected.text and
       (utf8.len(selected.text) or #selected.text) or 0

   -- Only select from a multi-character phrase. For a single-character
   -- candidate, fall through so < and > can still open the punctuation menu.
   if (selected_len <= 1) then
      return 2 -- kNoop
   end

   if (key_matches(key, first_key) and commit_text ~= "") then
      engine:commit_text(get_commit_text(context, first_character))
      -- reset ascii_composer's single-Shift-tap timer without switching mode
      engine:process_key(KeyEvent(0, 0))

      return 1 -- kAccepted
   end

   if (key_matches(key, last_key) and commit_text ~= "") then
      engine:commit_text(get_commit_text(context, last_character))
      -- reset ascii_composer's single-Shift-tap timer without switching mode
      engine:process_key(KeyEvent(0, 0))

      return 1 -- kAccepted
   end

   return 2 -- kNoop
end

return select_character

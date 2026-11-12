-- Reorder candidates for a complete quick5 code input.
--
-- A complete code is:
--   dakk   (2 pinyin letters + 2 shape letters)
--   yu/mi  (2 pinyin letters + "/" + 2 shape letters)
--
-- Desired order:
--   1. phrases (multi-character candidates covering the whole input)
--   2. the single character whose full code exactly matches the input
--   3. other candidates (same phonetic reading, different shape code)
--
-- `comment_format` reduces a candidate comment to the last shape code,
-- so the full-code character can be found by comparing its comment with
-- the shape part of the input.

local cangjie = {
  a = '日', b = '月', c = '金', d = '木', e = '水', f = '火', g = '土',
  h = '竹', i = '戈', j = '十', k = '大', l = '中', m = '一', n = '弓',
  o = '人', p = '心', q = '手', r = '口', s = '尸', t = '廿', u = '山',
  v = '女', w = '田', x = '難', y = '卜', z = '符',
}

function code_order_filter(input, env)
  local text = env.engine.context.input
  local is_code = text:match("^%l%l%l%l$") or text:match("^%l%l/%l%l$")
  if not is_code then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  local input_len = #text
  local shape = text:match("^%l%l(%l%l)$") or text:match("^%l%l/(%l%l)$")

  local phrases, fullchars, others = {}, {}, {}
  for cand in input:iter() do
    local text_len = utf8.len(cand.text) or #cand.text
    local at_start = cand._start == 0
    local is_fullchar = at_start and text_len == 1 and
        (cand._end == input_len or
         (cand.comment ~= "" and cand.comment == shape))
    if is_fullchar then
      table.insert(fullchars, cand)
    elseif at_start and cand._end == input_len and text_len > 1 then
      table.insert(phrases, cand)
    else
      table.insert(others, cand)
    end
  end

  for _, cand in ipairs(phrases) do
    yield(cand)
  end
  for _, cand in ipairs(fullchars) do
    yield(cand)
  end
  for _, cand in ipairs(others) do
    yield(cand)
  end
end

-- Optional: translate shape-code comments into Chinese Cangjie radicals.
-- Toggled by the `cangjie_comment` switch (字母 / 字根).
function cangjie_comment_filter(input, env)
  if not env.engine.context:get_option('cangjie_comment') then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  for cand in input:iter() do
    local genuine = cand:get_genuine()
    local c = genuine and genuine.comment or cand.comment
    if c and c ~= '' and c:match('^~?[a-z ]+$') then
      local translated = c:gsub('%l', cangjie)
      if genuine then
        genuine.comment = translated
      end
      cand.comment = translated
    end
    yield(cand)
  end
end

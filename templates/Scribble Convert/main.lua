-- Scribble Convert -- unit converter in notebook sketch style (240x320 VXP)
local E = engine
local A = require("src.art")
local U = require("src.units")

-- focus: 1=category, 2=from, 3=to, 4=input
local F_CAT, F_FROM, F_TO, F_IN = 1, 2, 3, 4

local S = {
    cat = 1,
    from = 3,   -- default m
    to = 2,     -- default cm
    focus = F_IN,
    buf = "1",  -- input buffer as string
    bye = false,
    bye_t = 0,
    toast = nil,
    toast_t = 0,
}

local function flash(msg)
    S.toast = msg
    S.toast_t = 1.2
end

local function parse_buf()
    if S.buf == "" or S.buf == "-" or S.buf == "." or S.buf == "-." then
        return 0
    end
    local v = tonumber(S.buf)
    if not v then return 0 end
    return v
end

local function result_str()
    local v = U.convert(S.cat, S.from, S.to, parse_buf())
    return U.fmt(v)
end

local function cycle_unit(delta)
    local n = U.count(S.cat)
    if S.focus == F_FROM then
        S.from = S.from + delta
        if S.from < 1 then S.from = n elseif S.from > n then S.from = 1 end
        if S.from == S.to then
            S.to = S.from + delta
            if S.to < 1 then S.to = n elseif S.to > n then S.to = 1 end
        end
    elseif S.focus == F_TO then
        S.to = S.to + delta
        if S.to < 1 then S.to = n elseif S.to > n then S.to = 1 end
        if S.to == S.from then
            S.from = S.to + delta
            if S.from < 1 then S.from = n elseif S.from > n then S.from = 1 end
        end
    end
end

local function swap_units()
    S.from, S.to = S.to, S.from
    flash("Doi cho")
end

local function set_cat(c)
    if c < 1 then c = U.CAT_COUNT elseif c > U.CAT_COUNT then c = 1 end
    S.cat = c
    -- sensible defaults per category
    if c == 1 then
        S.from, S.to = 3, 2      -- m -> cm
    elseif c == 2 then
        S.from, S.to = 3, 2      -- kg -> g
    else
        S.from, S.to = 2, 1      -- USD -> VND
    end
end

local function digit(d)
    if S.focus ~= F_IN then
        S.focus = F_IN
    end
    if #S.buf >= 12 then return end
    -- leading zero cleanup
    if S.buf == "0" then S.buf = "" end
    S.buf = S.buf .. d
end

local function add_dot()
    if S.focus ~= F_IN then S.focus = F_IN end
    if #S.buf >= 12 then return end
    if string.find(S.buf, "%.", 1, false) then return end
    if S.buf == "" then S.buf = "0" end
    S.buf = S.buf .. "."
end

local function backspace()
    if #S.buf <= 1 then
        S.buf = ""
    else
        S.buf = string.sub(S.buf, 1, #S.buf - 1)
    end
end

local function clear_buf()
    S.buf = ""
    flash("Xoa")
end

local function cycle_focus()
    S.focus = S.focus + 1
    if S.focus > F_IN then S.focus = F_CAT end
end

-- ------------------------------------------------------------------ layout
local TAB_Y = 28
local FRAME_Y = 48
local FRAME_H = 56
local FRAME_W = 96
local FROM_X = 16
local TO_X = 128
local ARROW_Y = FRAME_Y + FRAME_H / 2

local IN_LABEL_Y = 116
local IN_BOX_Y = 128
local IN_BOX_H = 28
local OUT_LABEL_Y = 164
local OUT_BOX_Y = 176
local OUT_BOX_H = 28
local NOTE_Y = 216
local NOTE2_Y = 232
local HINT_Y = 252

local function draw_tabs()
    local names = U.CAT_NAMES
    local i = 1
    local x = 34
    while i <= U.CAT_COUNT do
        local label = names[i]
        local w = A.tw(label) + 10
        local sel = (S.cat == i)
        local focused = sel and S.focus == F_CAT
        if sel then
            A.fill(x - 2, TAB_Y - 2, w + 4, 14, A.SHADOW)
        end
        A.outline(x - 2, TAB_Y - 2, w + 4, 14, focused and A.PEN or A.PENCIL2, 0.5)
        A.set_font(8)
        A.text(x + 3, TAB_Y, label, sel and (focused and A.PEN or A.INK) or A.LEAD2)
        if sel then
            A.stroke(x - 2, TAB_Y + 13, x + w + 2, TAB_Y + 14, A.RED, 0.6)
        end
        x = x + w + 6
        i = i + 1
    end
end

local function draw_frames()
    local fs = U.symbol(S.cat, S.from)
    local ts = U.symbol(S.cat, S.to)
    A.pencil_frame(FROM_X, FRAME_Y, FRAME_W, FRAME_H, "GOC", fs, S.focus == F_FROM)
    A.pencil_frame(TO_X, FRAME_Y, FRAME_W, FRAME_H, "DICH", ts, S.focus == F_TO)
    -- blue ballpoint arrow between the two pencil rectangles
    A.pen_arrow(FROM_X + FRAME_W + 4, ARROW_Y, TO_X - 4, A.PEN)
end

local function draw_fields()
    local fs = U.symbol(S.cat, S.from)
    local ts = U.symbol(S.cat, S.to)

    A.set_font(8)
    A.text(34, IN_LABEL_Y, "Nhap:", A.LEAD)
    A.sunk_box(34, IN_BOX_Y, 172, IN_BOX_H, S.focus == F_IN)
    local shown = S.buf
    if shown == "" then shown = "0" end
    A.set_font(14)
    local w = A.tw(shown)
    A.text(190 - w, IN_BOX_Y + 7, shown, S.focus == F_IN and A.INK or A.LEAD)
    if S.focus == F_IN then
        -- caret at append point (right edge of right-aligned value)
        A.stroke(192, IN_BOX_Y + 6, 192, IN_BOX_Y + 22, A.RED, 0)
    end
    A.set_font(8)
    A.text(40, IN_BOX_Y + 8, fs, A.PEN)

    A.set_font(8)
    A.text(34, OUT_LABEL_Y, "Ket qua:", A.LEAD)
    A.sunk_box(34, OUT_BOX_Y, 172, OUT_BOX_H, false)
    A.set_font(14)
    A.rtext(190, OUT_BOX_Y + 7, result_str(), A.PEN)
    A.set_font(8)
    A.text(40, OUT_BOX_Y + 8, ts, A.PEN)
end

local function draw_notes()
    -- faint handwritten conversion formulas
    A.note(36, NOTE_Y, U.formula_line(S.cat, S.from, S.to), 0.18)
    A.note(36, NOTE2_Y, U.work_line(S.cat, S.from, S.to), -0.12)
    -- margin scribble / teacher note feel
    A.note(36, HINT_Y, "tinh offline - ty gia co dinh", 0.1)
    if S.cat == 3 then
        A.note(36, HINT_Y + 14, "rates: fixed local snapshot", 0.08)
    end
end

local function draw_toast()
    if not S.toast or S.toast_t <= 0 then return end
    local w = A.tw(S.toast) + 16
    local x = (A.W - w) / 2
    local y = 96
    A.fill(x, y, w, 20, A.PAPER)
    A.outline(x, y, w, 20, A.INK, 0.8)
    A.fill(x + 4, y - 2, 12, 5, E.color(232, 182, 54))
    A.ctext(A.W / 2, y + 6, S.toast, A.PEN)
end

local function soft_labels()
    if S.focus == F_IN then
        return "Xoa", "Thoat", "5:chuyen"
    end
    return "Doi cho", "Thoat", "5:chuyen"
end

-- ------------------------------------------------------------------ lifecycle
function E.load()
    A.set_font(8)
    set_cat(1)
    S.buf = "1"
    S.focus = F_IN
end

function E.update(dt)
    if S.bye then
        S.bye_t = S.bye_t + dt
        if S.bye_t > 0.35 and E.exit then
            E.exit()
        end
        return
    end
    if S.toast_t > 0 then
        S.toast_t = S.toast_t - dt
        if S.toast_t <= 0 then S.toast = nil end
    end
end

function E.draw()
    A.jit_reset(20240917)
    A.paper()
    A.header("DOI DON VI", 6)
    draw_tabs()
    draw_frames()
    draw_fields()
    draw_notes()
    draw_toast()
    local l, r, c = soft_labels()
    A.softkeys(l, r, c)
    if E.flush then E.flush() end
end

function E.keypressed(k)
    if S.bye then return end
    k = tostring(k or "")

    local is_digit = (#k == 1 and k >= "0" and k <= "9")
    -- On the keypad 2/4/6/8 double as d-pad; only type them while editing.
    local pad_nav = (k == "2" or k == "4" or k == "6" or k == "8")

    if is_digit then
        if S.focus == F_IN then
            digit(k)
            return
        end
        if pad_nav then
            -- fall through to navigation below
        else
            digit(k)
            return
        end
    end

    if k == "*" then
        if S.focus == F_IN then
            add_dot()
        else
            swap_units()
        end
        return
    end

    if k == "#" then
        clear_buf()
        return
    end

    if k == "ok" or k == "5" then
        cycle_focus()
        return
    end

    if k == "up" or k == "2" then
        if S.focus == F_FROM or S.focus == F_TO then
            cycle_unit(-1)
        elseif S.focus == F_CAT then
            set_cat(S.cat - 1)
        end
        return
    end

    if k == "down" or k == "8" then
        if S.focus == F_FROM or S.focus == F_TO then
            cycle_unit(1)
        elseif S.focus == F_CAT then
            set_cat(S.cat + 1)
        end
        return
    end

    if k == "left" or k == "4" then
        if S.focus == F_CAT then
            set_cat(S.cat - 1)
        elseif S.focus == F_TO then
            S.focus = F_FROM
        elseif S.focus == F_IN then
            S.focus = F_TO
        end
        return
    end

    if k == "right" or k == "6" then
        if S.focus == F_CAT then
            set_cat(S.cat + 1)
        elseif S.focus == F_FROM then
            S.focus = F_TO
        elseif S.focus == F_TO then
            S.focus = F_IN
        end
        return
    end

    if k == "clear" or k == "back" then
        if S.focus == F_IN and #S.buf > 0 then
            backspace()
        elseif S.focus ~= F_CAT then
            S.focus = S.focus - 1
            if S.focus < F_CAT then S.focus = F_CAT end
        end
        return
    end

    if k == "softleft" then
        if S.focus == F_IN then
            clear_buf()
        else
            swap_units()
        end
        return
    end

    if k == "softright" then
        S.bye = true
        S.bye_t = 0
        return
    end
end

function E.keyreleased(k)
end

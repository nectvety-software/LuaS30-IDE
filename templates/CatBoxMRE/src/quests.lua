Quest = Quest or {}

Quest.skins = {
  {id=1,name="MIDNIGHT", body=0x1A2230, dark=0x111824, accent=0xF19AB3, unlock="Default"},
  {id=2,name="CALICO",   body=0xE7B071, dark=0x6B4630, accent=0xFFF2D0, unlock="Quest reward"},
  {id=3,name="SKY",      body=0x6EA8D8, dark=0x334D6D, accent=0xDDF4FF, unlock="Quest reward"},
  {id=4,name="PHANTOM",  body=0xB59AD8, dark=0x594B70, accent=0xF0E8FF, unlock="Quest reward"},
  {id=5,name="GOLDEN",   body=0xE5B94D, dark=0x7C5E26, accent=0xFFF1A8, unlock="Quest reward"},
  {id=6,name="ROSE",     body=0xE493AE, dark=0x7A4760, accent=0xFFE6F0, unlock="Shop purchase"},
  {id=7,name="EMERALD",  body=0x5DBF8A, dark=0x2E5F4D, accent=0xDCF6EA, unlock="Shop purchase"},
}

Quest.list = {
  {
    id=1, giver_level=1, giver="MIMI", title="GREEN HERO", reward_skin=2,
    steps={
      {
        label="STEP 1", desc="Earn 3 stars in Green Hills.",
        done=function() return WorldMap.world_star_total(1)>=3 end,
        progress=function() return WorldMap.world_star_total(1),3 end
      },
      {
        label="STEP 2", desc="Find the Box Attic secret.",
        done=function() return Save.get_secret(3)==1 end,
        progress=function() return Save.get_secret(3),1 end
      },
      {
        label="STEP 3", desc="Defeat Moss King.",
        done=function() return Save.get_star(7)>0 end,
        progress=function() return (Save.get_star(7)>0) and 1 or 0,1 end
      },
    }
  },
  {
    id=2, giver_level=8, giver="TIKO", title="SKY COURIER", reward_skin=3,
    steps={
      {
        label="STEP 1", desc="Earn 4 stars in Moving Skies.",
        done=function() return WorldMap.world_star_total(2)>=4 end,
        progress=function() return WorldMap.world_star_total(2),4 end
      },
      {
        label="STEP 2", desc="Find the Crusher Vault secret.",
        done=function() return Save.get_secret(10)==1 end,
        progress=function() return Save.get_secret(10),1 end
      },
      {
        label="STEP 3", desc="Defeat Picnic Brute.",
        done=function() return Save.get_star(13)>0 end,
        progress=function() return (Save.get_star(13)>0) and 1 or 0,1 end
      },
    }
  },
  {
    id=3, giver_level=14, giver="LUMA", title="GHOST WATCH", reward_skin=4,
    steps={
      {
        label="STEP 1", desc="Earn 4 stars in Ghost Garden.",
        done=function() return WorldMap.world_star_total(3)>=4 end,
        progress=function() return WorldMap.world_star_total(3),4 end
      },
      {
        label="STEP 2", desc="Find the Canyon Den secret.",
        done=function() return Save.get_secret(17)==1 end,
        progress=function() return Save.get_secret(17),1 end
      },
      {
        label="STEP 3", desc="Defeat Phantom Keeper.",
        done=function() return Save.get_star(19)>0 end,
        progress=function() return (Save.get_star(19)>0) and 1 or 0,1 end
      },
    }
  },
  {
    id=4, giver_level=20, giver="MIMI", title="TOWER LEGEND", reward_skin=5,
    steps={
      {
        label="STEP 1", desc="Earn 5 stars in Cat Tower.",
        done=function() return WorldMap.world_star_total(4)>=5 end,
        progress=function() return WorldMap.world_star_total(4),5 end
      },
      {
        label="STEP 2", desc="Find the Lift Loft secret.",
        done=function() return Save.get_secret(24)==1 end,
        progress=function() return Save.get_secret(24),1 end
      },
      {
        label="STEP 3", desc="Recover all 4 secret gems.",
        done=function() return Save.total_secrets()>=4 end,
        progress=function() return Save.total_secrets(),4 end
      },
    }
  },
}

Quest.shop_items = {
  {
    id="HEART", title="HEART CHARM", cost=30, max=2, desc="+1 life at level start.",
    owned=function() return Save.data.up_heart or 0 end,
    can_buy=function() return (Save.data.up_heart or 0) < 2 end,
    buy=function() Save.data.up_heart=(Save.data.up_heart or 0)+1 end,
    info=function() return tostring(3+(Save.data.up_heart or 0)).." START HP" end,
  },
  {
    id="MAGNET", title="COIN MAGNET", cost=40, max=1, desc="Pull coins from farther away.",
    owned=function() return Save.data.up_magnet or 0 end,
    can_buy=function() return (Save.data.up_magnet or 0) < 1 end,
    buy=function() Save.data.up_magnet=1 end,
    info=function() return ((Save.data.up_magnet or 0)==1) and "ACTIVE" or "LOCKED" end,
  },
  {
    id="BELL", title="GUARD BELL", cost=55, max=1, desc="Start every level with 1 shield.",
    owned=function() return Save.data.up_bell or 0 end,
    can_buy=function() return (Save.data.up_bell or 0) < 1 end,
    buy=function() Save.data.up_bell=1 end,
    info=function() return ((Save.data.up_bell or 0)==1) and "ACTIVE" or "LOCKED" end,
  },
}

Quest.shop_skins = {
  {skin_id=6, cost=45, desc="Rose shop skin"},
  {skin_id=7, cost=60, desc="Emerald shop skin"},
}

function Quest.get(id)
  return Quest.list[id]
end

function Quest.for_npc(level,name)
  for i=1,#Quest.list do
    local q=Quest.list[i]
    if q.giver_level==level and q.giver==name then return q end
  end
  return nil
end

function Quest.state(id)
  return Save.get_quest(id)
end

function Quest.is_skin_unlocked(id)
  return Save.get_skin(id)==1
end

function Quest.unlock_skin(id)
  Save.set_skin(id,1)
end

function Quest.step_index(q)
  local st=Save.get_quest(q.id)
  if st<=0 then return 1 end
  if st>#q.steps then return #q.steps end
  return st
end

function Quest.step_summary(q)
  local st=Save.get_quest(q.id)
  if st<=0 then st=1 end
  if st>#q.steps then
    return "COMPLETE","Reward: "..Quest.skins[q.reward_skin].name
  end
  local step=q.steps[st]
  local n,max=step.progress()
  return step.label.." "..q.title, tostring(n).."/"..tostring(max).." "..step.desc
end

function Quest.talk(level,name)
  local q=Quest.for_npc(level,name)
  if not q then return nil,nil end
  local st=Save.get_quest(q.id)

  if st==0 then
    Save.set_quest(q.id,1)
    Save.write()
    local step=q.steps[1]
    return "QUEST START",step.label.." "..step.desc
  end

  if st>=1 and st<=#q.steps then
    local step=q.steps[st]
    if step.done() then
      if st==#q.steps then
        Save.set_quest(q.id,#q.steps+1)
        Quest.unlock_skin(q.reward_skin)
        Save.write()
        return "QUEST COMPLETE","SKIN "..Quest.skins[q.reward_skin].name
      else
        Save.set_quest(q.id,st+1)
        Save.write()
        local next_step=q.steps[st+1]
        return "QUEST UPDATED",next_step.label.." "..next_step.desc
      end
    else
      local n,max=step.progress()
      return step.label.." "..q.title,tostring(n).."/"..tostring(max).." "..step.desc
    end
  end

  return "QUEST COMPLETE","SKIN "..Quest.skins[q.reward_skin].name
end

function Quest.active_summary()
  for i=1,#Quest.list do
    local q=Quest.list[i]
    local st=Save.get_quest(q.id)
    if st>=1 and st<=#q.steps then
      local step=q.steps[st]
      local n,max=step.progress()
      return q.title,tostring(n).."/"..tostring(max)
    end
  end
  return "NO ACTIVE QUEST","Talk to NPCs"
end

function Quest.unlocked_skin_ids()
  local r={}
  for i=1,#Quest.skins do
    if Save.get_skin(i)==1 then r[#r+1]=i end
  end
  return r
end

function Quest.find_shop_skin(id)
  for i=1,#Quest.shop_skins do
    local s=Quest.shop_skins[i]
    if s.skin_id==id then return s end
  end
  return nil
end

function Quest.buy_shop_skin(id)
  local offer=Quest.find_shop_skin(id)
  if not offer then return false,"UNAVAILABLE" end
  if Save.get_skin(id)==1 then return false,"ALREADY OWNED" end
  if (Save.data.wallet or 0) < offer.cost then return false,"NEED "..offer.cost.." COINS" end
  if not Save.spend_wallet(offer.cost) then return false,"NOT ENOUGH COINS" end
  Save.set_skin(id,1)
  Save.write()
  return true,"BOUGHT "..Quest.skins[id].name
end

function Quest.buy_shop_item(index)
  local item=Quest.shop_items[index]
  if not item then return false,"UNAVAILABLE" end
  if not item.can_buy() then return false,"MAXED" end
  if (Save.data.wallet or 0) < item.cost then return false,"NEED "..item.cost.." COINS" end
  if not Save.spend_wallet(item.cost) then return false,"NOT ENOUGH COINS" end
  item.buy()
  Save.write()
  return true,"BOUGHT "..item.title
end

function Quest.shop_entry_count()
  return #Quest.shop_items + #Quest.shop_skins
end

function Quest.shop_entry(index)
  if index<=#Quest.shop_items then
    local item=Quest.shop_items[index]
    return {
      kind="item",
      title=item.title,
      cost=item.cost,
      desc=item.desc,
      status=item.info(),
    }
  end
  local offer=Quest.shop_skins[index-#Quest.shop_items]
  local skin=Quest.skins[offer.skin_id]
  return {
    kind="skin",
    title=skin.name,
    cost=offer.cost,
    desc=offer.desc,
    status=(Save.get_skin(offer.skin_id)==1) and "OWNED" or "FOR SALE",
    skin_id=offer.skin_id
  }
end


function Quest.quest_count()
  return #Quest.list
end

function Quest.quest_status_text(q)
  local st=Save.get_quest(q.id)
  if st<=0 then return "NOT STARTED" end
  if st<=#q.steps then return "STEP "..st.."/"..#q.steps end
  return "COMPLETE"
end

function Quest.log_entry(index)
  local q=Quest.list[index]
  if not q then return nil end
  local st=Save.get_quest(q.id)
  local status=Quest.quest_status_text(q)
  local line1=""
  local line2="Reward: "..Quest.skins[q.reward_skin].name
  if st<=0 then
    line1=q.steps[1].desc
  elseif st<=#q.steps then
    local step=q.steps[st]
    local n,max=step.progress()
    line1=step.label.." "..q.title
    line2=tostring(n).."/"..tostring(max).." "..step.desc
  else
    line1="Reward unlocked."
  end
  return {
    id=q.id,
    title=q.title,
    giver=q.giver,
    status=status,
    reward=Quest.skins[q.reward_skin].name,
    line1=line1,
    line2=line2,
    step=(st<=0) and 1 or ((st>#q.steps) and #q.steps or st),
    total=#q.steps
  }
end

# 已知偏移表 (known-offsets)

> 来源:原 C# 编辑器 `Offsets.cs`,已由 `tools/extract.py` 提取。
> 格式: `名称 | 偏移(hex) | 大小/说明`。此文件是 AI 逆向研究的知识固话区,
> 新验证的偏移请追加到对应小节,并标记验证人/日期。

## 已知偏移

| 名称 | 偏移 | 说明 |
| --- | --- | --- |
| FIRST_CHAR_SLOT_USED | 0x4 | Header Data Size 1 |
| SECOND_CHAR_SLOT_USED | 0x5 | Size 1 |
| THIRD_CHAR_SLOT_USED | 0x6 | Size 1 |
| FIRST_CHARACTER_OFFSET | 0x10 | Size 4 |
| SECOND_CHARACTER_OFFSET | 0x14 | Size 4 |
| THIRD_CHARACTER_OFFSET | 0x18 | Size 4 |
| NAME_OFFSET | 0x23B7D | Character Offsets [CHARACTER BASE +  CHARACTER OFFSET] size 4 |
| PLAY_TIME_OFFSET | 0x20 | Size 4m this only shows on the save screen |
| PLAY_TIME_OFFSET2 | 0x2248B | Size 4 |
| FUNDS_OFFSET | 0x24 | Size 4, this only shows on the save screen |
| FUNDS_OFFSET2 | 0x280F | size 4 |
| HUNTER_RANK_OFFSET | 0x28 | Size 2 |
| CHARACTER_VOICE_OFFSET | 0x23B48 | Size 1 |
| CHARACTER_EYE_COLOR_OFFSET | 0x23B49 | Size 1 |
| CHARACTER_CLOTHING_OFFSET | 0x23B4A | Size 1 |
| CHARACTER_GENDER_OFFSET | 0x23B4B | Size 1 |
| CHARACTER_HUNTINGSTYLE_OFFSET | 0x23B4C | Size 1 |
| CHARACTER_HAIRSTYLE_OFFSET | 0x23B4D | Size 1 |
| CHARACTER_FACE_OFFSET | 0x23B4E | Size 1 |
| CHARACTER_FEATURES_OFFSET | 0x23B4F | Size 1 |
| CHARACTER_SKIN_COLOR_OFFSET | 0x23B67 | Size 4 |
| CHARACTER_FEATURES_COLOR_OFFSET | 0x23B6F | Size 4 |
| PALICO_OFFSET | 0x23BB6 | Palico Size 27216 (84 of them each 324 bytes long) |
| HR_POINTS_OFFSET | 0x280B | Points Size 4 |
| ACADEMY_POINTS_OFFSET | 0x2817 | Size 4 |
| BHERNA_POINTS_OFFSET | 0x281B | Size 4 |
| KOKOTO_POINTS_OFFSET | 0x281F | Size 4 |
| POKKE_POINTS_OFFSET | 0x2823 | Size 4 |
| YUKUMO_POINTS_OFFSET | 0x2827 | Size 4 |
| MONSTERHUNT_OFFSETS | 0x5EA6 | Monster Hunts / Sizes Size 274, 137 Monsters (supposedly) 2 bytes each |
| MONSTERCAPTURE_OFFSETS | 0x5FB8 | Size 274,137 Monsters (supposedly) 2 bytes each |
| MONSTERSIZE_OFFSETS | 0x60CA | Size 548, 4 bytes per monster |
| ITEM_BOX_OFFSET | 0x278 | Items, Equips, Pouch Size 5463 (2300 of them each 19 bits long) |
| EQUIPMENT_BOX_OFFSET | 0x62EE | Size 72000 (2000 of them each 36 bytes long) |
| PALICO_EQUIPMENT_OFFSET | 0x17C2E | Size 36000 (1000 of them 36 bytes long) |
| GUILCARD_OFFSET | 0xC71BD | Player Guild Card |
| GUILDCARD_HUNTINGSTYLE_OFFSET | 0xC71DA | public const int GUILDCARD_WEAPONTYPE_OFFSET = 0XC71D5; //Size 1 Size 1 |
| GUILDCARD_HAIRSTYLE_OFFSET | 0xC71DB | Size 1 |
| GUILDCARD_FACE_OFFSET | 0xC71DC | Size 1 |
| GUILDCARD_FEATURES_OFFSET | 0xC71DD | Size 1 |
| GUILDCARD_ARENA_LOG_OFFSET | 0xC83E1 | public const int GUILDCARD_ARENA_WEAPON_OFFSET = 0XC7AB3; //Size 30 Size 324 |
| MANUAL_SHOUTOUT_OFFSETS | 0x11D629 | Shoutouts Size 60 |
| AUTOMATIC_SHOUTOUT_OFFSETS | 0x11E169 | Size 60 |


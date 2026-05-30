# Character ID Index

Этот файл фиксирует стабильные ID персонажей для предыстории Академии Астрейн.

ИИ обязан использовать эти ID в памяти, отношениях, репутации, силе, NPC registry и сценовых обновлениях.

Нельзя менять ID после появления персонажа.

## Main cast

| ID | Имя | Статус | Примечание |
|---|---|---|---|
| `akira` | Акира Акацуми / Акира Картер | player / main | Героиня, скрывает способности и природу, сама не знает всей правды. |
| `raiden_sterling` | Райден Стэрлинг | main / romance / military elite | 31 августа, гибрид, сам не знает; не философ, ленивый грубиян с дисциплиной. |
| `haru_foster` | Хару Фостер | main / romance / social bridge | Огонь/жар, друг Райдена, влюбляется в Акиру, не дурачок. |
| `samuel_sterling` | Самуэль Стэрлинг | main antagonist / commander | Брат Райдена, командир элитных городских рейдов и направления против кайросов. |
| `ray_carter` | Рэй Картер | main / family / commander | Сын Джуна, знает часть правды об Акире. |
| `jun_carter` | Джун Картер | main / father / sector commander | Командующий Восточным сектором, отец Рэя, приёмный отец Акиры. |
| `livia_cross` | Ливия Кросс | main supporting / friend / social square | Подруга Акиры, сначала увлечена Райденом, потом переключается на Хару. |
| `eiren_vale` | Эйрен Вейл / Наблюдатель | hidden / observer | Человеческая маска Наблюдателя, абсолютный hidden lore. |
| `daniel_dante_weiss` | Даниэль “Данте” Вэйс | main supporting / sound / scout | Курсант 19 лет, звук/вибрация, ближне-средний бой, разведка, боится потерять контроль над радиусом энергии. |
| `elias_aster` | Эльяс Астер | main supporting / Aster twin / reflection | Один из двойняшек Астер; энергия отражения, тревожная социальная линия, провокатор и наблюдатель. |
| `seline_aster` | Селин Астер | main supporting / Aster twin / distortion | Одна из двойняшек Астер; энергия искажения, сбивает восприятие пространства и внимания. |
| `kael_north` | Каэл Норт | academy staff / tactics instructor | Преподаватель тактики, куратор старших групп, бывший рейдер, энергия вектор/траектория. |
| `kiara_volt` | Киара Вольт | main supporting / social rival / Livia rival | Курсантка 18 лет, магнитное смещение, социальная соперница Ливии, крутится рядом с Райденом и Хару. |
| `noa_rian` | Ноа Риан | main supporting / quiet romantic protector | Курсант 19 лет, задержка/отложенное действие, тихий мягкий защитник Акиры. |
| `veronica_ellard` | Вероника Эллард | main supporting / Akira rival / status conflict | Курсантка 17 лет, давление/кинетический импульс, соперница Акиры через статус, силу и публичное превосходство. |

## Main character card files

Этот список должен соответствовать фактическим карточкам в `characters/main/`.

| Card file | Stable ID / IDs |
|---|---|
| `characters/main/akira.md` | `akira` |
| `characters/main/daniel_dante_weiss.md` | `daniel_dante_weiss` |
| `characters/main/elias_seline_aster.md` | `elias_aster`, `seline_aster` |
| `characters/main/haru_foster.md` | `haru_foster` |
| `characters/main/jun_carter.md` | `jun_carter` |
| `characters/main/kael_north.md` | `kael_north` |
| `characters/main/kiara_volt.md` | `kiara_volt` |
| `characters/main/livia_cross.md` | `livia_cross` |
| `characters/main/noa_rian.md` | `noa_rian` |
| `characters/main/raiden_sterling.md` | `raiden_sterling` |
| `characters/main/ray_carter.md` | `ray_carter` |
| `characters/main/samuel_sterling.md` | `samuel_sterling` |
| `characters/main/veronica_ellard.md` | `veronica_ellard` |

## Important recurring NPC / key candidates

| ID | Имя | Статус | Примечание |
|---|---|---|---|
| `asher_lane` | Ашер Лейн | recurring / key_candidate / Livia school past | Бывший Ливии; старшекурсник, возвращается 1 сентября 1198 после отсутствия в августе; связан со старшей компанией и “Слепой зоной”. |
| `kai_renwick` | Кай Ренвик | recurring / key_candidate / Akira school past | Парень из школьного прошлого Акиры; связан с историей “Ставка закрыта” и каналом “Слепая зона”; возвращается 1 сентября 1198. |

## NPC / recurring card files

| Card file | Stable ID / IDs |
|---|---|
| `characters/npc/asher_lane.md` | `asher_lane` |
| `characters/npc/kai_renwick.md` | `kai_renwick` |

## Important family / future cards

| ID | Имя | Статус | Примечание |
|---|---|---|---|
| `raiden_mother` | Родная мать Райдена | hidden / deceased / future mystery | Бывшая командующая направлением, где поднимается Самуэль; официально самоубийство. |
| `raiden_father` | Отец Райдена и Самуэля | political / family pressure | Богатая влиятельная фигура; имя уточнить. |
| `akira_biological_mother` | Мать Акиры | hidden / deceased | Умерла при родах; детали уточнить позже. |

## NPC ID rules

NPC ID пишется латиницей в формате `lowercase_snake_case`.

Формула:

```txt
first_name_last_name
```

Если у персонажа пока нет фамилии, временно использовать:

```txt
first_name_role
```

Но после закрепления фамилии ID лучше стабилизировать и больше не менять.

## Naming rules

В сцене имена пишутся русскими буквами.

Сами имена должны звучать японско-европейски, не по-русски.

Не использовать имена из старых сессий, тестовых новелл или другой игры, если персонаж не внесён в этот репозиторий.

Не считать пример имени каноном. Каноном персонаж становится только после добавления в:

- этот индекс;
- `characters/npc/npc_registry.md`;
- отдельную карточку персонажа.

## Promotion rules

Если NPC появился один раз без влияния — можно держать в scene notes.

Если NPC:

- получил имя;
- повторно появился;
- вступил в конфликт;
- стал объектом симпатии/ревности;
- дал важную улику;
- стал соперником;
- связан с Самуэлем, академией, кайросами или Эхо;
- повлиял на отношения главных;

его нужно добавить в `characters/npc/npc_registry.md`.

Если NPC стал важным для арки — вынести в отдельную карточку:

```txt
characters/npc/<id>.md
```

## Knowledge rule

ID персонажа не означает, что он знает скрытый лор.

Каждому персонажу нужно отдельно фиксировать:

- что знает публично;
- что видел лично;
- что ему рассказали;
- что он подозревает;
- что он не знает.

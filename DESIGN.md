---
name: GAC Connect cards
description: Home Assistant dashboard cards for GAC cars, drawn as a road atlas.
colors:
  land: "#eaf0e2"
  paper: "#f8faf4"
  water: "#dce6ec"
  ink: "#1e2421"
  muted: "#535b56"
  hair: "rgba(30, 36, 33, 0.2)"
  edge: "rgba(30, 36, 33, 0.34)"
  motorway: "#2e6db4"
  motorway-case: "#1b3f6b"
  motorway-ink: "#ffffff"
  primary-green: "#1f8a4c"
  primary-green-case: "#145c33"
  a-road-red: "#d2352b"
  a-road-red-case: "#8e1f18"
  a-road-red-ink: "#b02a21"
  b-road-yellow: "#f2c230"
  b-road-yellow-case: "#8a6a0a"
  minor-road: "#ffffff"
  minor-road-case: "#a9b4a3"
  plan-body: "#f8faf4"
  plan-glass: "#dce6ec"
typography:
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "40px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.01em"
    fontFeature: "tnum, lnum"
  headline:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.05em"
  title:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1
    fontFeature: "tnum"
  control:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "0.02em"
  body:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.35
  body-small:
    fontFamily: "Barlow, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontFamily: "Barlow Condensed, Arial Narrow, Roboto Condensed, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: "16px"
    letterSpacing: "0.1em"
rounded:
  track: "1px"
  control: "2px"
  card: "4px"
  junction: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  plate: "44px"
  target: "48px"
components:
  card:
    backgroundColor: "{colors.land}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    typography: "{typography.body}"
  name-plate:
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
    height: "{spacing.plate}"
    padding: "0 16px"
  action:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    typography: "{typography.control}"
    height: "{spacing.target}"
    padding: "0 8px"
  action-on:
    backgroundColor: "{colors.motorway}"
    textColor: "{colors.motorway-ink}"
  action-pending:
    backgroundColor: "{colors.water}"
    textColor: "{colors.motorway-case}"
  action-refused:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.a-road-red-ink}"
  segment:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "44px"
    padding: "0 4px"
  segment-selected:
    backgroundColor: "{colors.motorway}"
    textColor: "{colors.motorway-ink}"
  stepper:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    typography: "{typography.title}"
    height: "{spacing.target}"
  time-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    typography: "{typography.title}"
    height: "{spacing.target}"
    padding: "0 10px"
  day-chip:
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    height: "44px"
  day-chip-on:
    backgroundColor: "{colors.motorway}"
    textColor: "{colors.motorway-ink}"
  switch-track:
    backgroundColor: "{colors.minor-road}"
    rounded: "{rounded.track}"
    width: "48px"
    height: "16px"
  switch-track-on:
    backgroundColor: "{colors.motorway}"
---

# Design System: GAC Connect cards

## Overview

**Creative North Star: "The Strip-Map Atlas"**

Every reading that has length is a road. Battery charge is a cased neutral road filled to its level, with no thumb, and the range written as an atlas distance marker between two junction triangles. A charging window is a motorway stretch on a 24-hour road whose two ends are dragged; the cabin-to-target temperature gap is an arrow along the temperature road, the stretch the A/C will drive; fan speeds and other ordered choices are junctions along a road, driven up to the chosen one; the day's history runs down a minor road with a mark at each event. The card ground is flat land tint, the way an atlas page is, and the road classes are the only colours.

The cards are dense and operational: narrow (300 to 420 px), stacked in Home Assistant columns, read at a glance on a phone or wall tablet. Labels are condensed capitals like the print on a map, figures are tabular, and prose is plain Barlow. Nothing floats: one-pixel hairlines divide sections, and depth comes from road casing, never from shadow. The world explicitly refuses the category default of dark glass tiles over a hero render with a ring gauge.

Light and dark are both first-class: day atlas (land tint, white minor roads, dark casings) and night atlas (slate ground, dim minor roads, pale casings). The card follows Home Assistant's dark mode through a `dark` attribute on the host.

**Key Characteristics:**
- Readings with length drawn as cased roads with junctions and distance markers.
- Road classes are the palette: motorway blue, primary-route green, A-road red, B-road yellow, the neutral road, minor road white.
- Barlow Condensed capitals for labels, figures and controls; Barlow for prose.
- Flat land-tint card, one-pixel hairlines, no shadows.
- Square-shouldered controls (2 px corners), 48 px targets, 8 px grid.
- A command in flight is a road under construction: dashed, marching casing.

## Colors

An atlas palette: a pale land ground, a near-black ink, and four road classes that each carry exactly one meaning.

### Primary
- **Motorway Blue** (motorway, cased by motorway-case): what the owner can change, and nothing else. The selected segment, an on action, an on switch track, chosen charging days, the draggable charging window and quiet hours, the driven part of a stops road, a command in flight, focus rings and text selection. Text on it is motorway-ink.
- **Neutral Road** (road, cased by road-case; #56625b on #2f3833 by day, #aeb9b1 on #dfe6dd by night): readings. The battery road at normal charge, the temperature arrow, a read-only charging window. A reading never carries a thumb or junction that could pass for a handle.

### Secondary
- **Primary-Route Green** (primary-green, cased by primary-green-case): healthy and charging. The battery road while charging, the square "fine" mark, confirmed history entries.

### Tertiary
- **A-Road Red** (a-road-red, cased by a-road-red-case): faults and refusals. The battery road at 10 % or below, the fault triangle, a refused action's border. Red text uses a-road-red-ink, which holds contrast on land tint.
- **B-Road Yellow** (b-road-yellow, cased by b-road-yellow-case): warnings and open things. The battery road at 20 % or below, the warning triangle, open doors, boot and windows on the car plan.

### Neutral
- **Land Tint** (land): the card ground.
- **Paper** (paper): the face of every control (action, segments, stepper, time field, select), one step lighter than land.
- **Water** (water): the map ground under the location card and the ground of a pending control.
- **Ink** (ink): text, junction rings, distance-marker triangles, tick marks.
- **Muted Ink** (muted): labels, units, descriptions, freshness line.
- **Hairline** (hair): section dividers, card border, segment dividers.
- **Edge** (edge): control borders, one step stronger than a hairline.
- **Minor Road** (minor-road, cased by minor-road-case): the empty part of every road, switch track when off, unchosen stops.
- **Plan Body / Plan Glass** (plan-body, plan-glass): fill of the car plan's bodywork and glazing.

### Night atlas
The dark theme redefines every token on the same names: land #17201b, paper #1f2a24, water #1a2a35, ink #e4ebe2, muted #a4aea7, hair rgba(228, 235, 226, 0.16), edge rgba(228, 235, 226, 0.3), motorway #3f86d4 cased #9cc4ef with ink #0c1a2b, green #34a866 cased #9ad9b2, red #e0493e cased #f3a49d with ink #f08a80, yellow #f2c230 cased #f7dd8a, minor road #2b3731 cased #4b5852, plan body #26322c, plan glass #1f3442. Casings flip from darker-than-fill (day) to paler-than-fill (night) so the road edge always reads against the ground.

### Named Rules
**The Road Class Rule.** Colour is only ever a road class, and each class means one thing: blue is something the owner can change, the neutral road is a reading, green is healthy or charging, red is a fault or refusal, yellow is a warning or something open. No decorative colour, no gradients, no brand accent.

**The Casing Rule.** A coloured fill is always cased by its darker (day) or paler (night) partner: roads at 14 px casing under 10 px fill, selected controls with a 1 px case-coloured edge. A fill without its casing is not a road.

**The Shape-Before-Colour Rule.** Every state mark has a shape as well as a colour: square for fine, triangle for attention or fault, dashed ring for waiting, open square for off, filled circle for information. Colour never carries state alone.

## Typography

**Display Font:** Barlow Condensed (with Arial Narrow, Roboto Condensed, sans-serif), weights 500, 600, 700
**Body Font:** Barlow (with system-ui, Segoe UI, Roboto, sans-serif), weights 400, 500

Both faces ship with the integration as latin and latin-ext woff2 subsets and are declared once in the document, because shadow roots cannot declare fonts. No runtime font fetch.

**Character:** Condensed capitals read like atlas print, tight and legible at small sizes in narrow columns; the plain humanist Barlow carries descriptions without competing.

### Hierarchy
- **Display** (600, 40px, line-height 1, tabular lining figures): the headline reading of a card. The battery percentage on the Vehicle card steps up to 48px; the Charging card's battery to 32px; 34px under 330 px container width. Units sit beside it at 18px 500 in muted ink.
- **Headline** (700, 22px, 0.05em, uppercase): the name plate title. The location card's place name uses the same voice at 28px.
- **Title** (600, 20 to 30px, tabular): secondary readings such as stepper values and time fields (22px), the charging window (30px), the last command (20px), tyre and cell figures (22 to 24px).
- **Control** (600, 16px, 0.02em): action button labels; segments at 15px; select at 16px.
- **Body** (Barlow 400, 15px, 1.35): row titles at 500; notes at 14px; descriptions and the freshness line at 13px muted.
- **Label** (Barlow Condensed 600, 12px/16px, 0.1em, uppercase, muted): names a reading or a group of controls (BATTERY, TARGET, FAN, TYRES). Road ticks and plan callouts use the same face at 12px with 0.06em.

### Named Rules
**The Tabular Figures Rule.** Every number that can change is set in Barlow Condensed with tabular lining numerals so readings do not jitter as they update.

**The Label Names A Value Rule.** The uppercase label exists to name the reading or control directly beneath or beside it, as a map legend names a feature. It is never a decorative line set above a headline.

## Layout

Each card is a vertical stack of sections inside a flat container: a 44 px name plate, body sections, and a freshness line at the foot. Sections are padded 12px 16px and divided by a single hairline. The card is an inline-size container, and layout responds to the card's own width, not the viewport.

- **Grid:** 8 px rhythm (4, 8, 12, 16). Action grids are 3 columns with 8 px gaps; paired figures sit in two- or three-column cells divided by vertical hairlines with 12 to 16 px left padding, the first cell flush.
- **Targets:** every control is at least 44 px tall, primary controls 48 px; list rows have a 48 px minimum.
- **At 380 px and below (Vehicle card):** the plan and the temperature column stack; the plan centres at up to 250 px wide and the two temperatures sit side by side under a hairline.
- **At 330 px and below:** horizontal padding drops from 16 to 12 px, the display figure drops to 34px, and the 3-column action grid becomes 2 columns.
- **Road drawings** are SVG sized in JavaScript to the measured inner width of the section (never narrower than 160 to 200 px), so the road always spans the card.
- Home Assistant grid sizing: 12 columns by default, 6 minimum, rows auto.

## Elevation & Depth

Flat. The card has `box-shadow: none`, a 1 px hairline border, and no elevation at rest, on hover, or in any state. Depth is conveyed by road casing: a coloured fill sitting on a wider, darker (or, at night, paler) casing stroke. Inset 1 px rings on selected segments and refused actions are casing, not shadow.

### Named Rules
**The Flat Atlas Rule.** No drop shadows, no blur, no glass, no layered surfaces. If something needs to stand forward, case it.

## Shapes

Square-shouldered. Cards have softly squared corners (4px); controls, fields, chips and selects have barely-there corners (2px); the switch track is nearly square (1px). The only true circles are junctions: switch knobs, stops, road junction dots and the target marker on the temperature road. Triangles are distance markers, the "now" pointer on the day road, and warning or fault marks. Icons are a single drawn stroke family: 20 by 20 viewbox, 1.5 px stroke, round caps and joins, current colour, drawn for the cards and not taken from a library. The name plate's grid-square badge is a 24 px square with a 1 px ink border holding the card's 16 px icon.

## Components

### Name plate
The card's title strip, like an atlas page header. Grid-square badge, card or car name in the headline voice, and a muted label at the right (the car's name, or the card's name on the Vehicle card), ellipsised at 45 % width. A hairline closes it.

### Freshness line
The foot of every card. A full-width button at least 32 px tall with a hairline above, 13px muted Barlow: an optional state mark, then what the car is doing and how old the report is ("Charging · Updated 4 min ago"). Faults (offline, sign in again) take the red triangle, warnings (refresh failed, rate limited, old report) the yellow triangle, quiet hours the open square. Opens the last-report entity.

### Action button
Tactile, square and plain: a 48 px paper face with an edge border, 2px corners, a 20 px stroke icon and a condensed label.
- **Hover / Active:** paper mixed with 12 % / 20 % ink. Transitions 150 ms ease-out on background, colour and border.
- **On:** motorway fill, motorway-ink text, motorway-case border.
- **Pending:** see the signature interaction below.
- **Refused:** red border with an inset 1 px red ring and red-ink text, held for two minutes after the refusal.
- **Unavailable:** muted text, dotted border, not-allowed cursor, with a hint explaining why.
- **Hold to confirm:** consequential actions (unlock, open boot, turn off, release cable) show a dashed underline inside the button. Pressing fills a 5 px motorway bar along the bottom over 700 ms; releasing early swaps the label to "Hold to confirm" for 1.8 s. Keyboard Enter or Space holds the same way.
- **Focus:** 2 px motorway outline, 2 px offset.

### Segments
A single paper strip with an edge border and hairline dividers; 44 px tall, condensed 15px labels. The selected segment fills motorway with an inset case ring. Arrow keys move the choice. Used for modes, seat ventilation and the fridge mode.

### Switch (a road)
Off is a 48 by 16 px minor road with its casing; on is a cased motorway (2 px case ring). The knob is a 20 px junction with a 1.5 px ink ring that slides 180 ms on cubic-bezier(0.2, 0.8, 0.2, 1). Pending replaces the track with water and a dashed motorway-case outline. Turning some switches on takes a hold. The hit area is 60 by 48 px.

### Stepper
Minus and plus 48 px squares around a centred value in the title voice, hairlines between, on a paper box. Taps change the shown value at once, in motorway-case while it is a draft, and send one request after 1.2 s.

### Stops (choices along a road)
A minor road with a junction for each option and the label beneath in 13px uppercase condensed. The road is driven in motorway up to the chosen junction, which grows to 19 px with a 2 px ink ring; passed junctions take motorway-case rings. Used for fan speed.

### Fields
Time inputs and selects share the control face: paper, edge border, 2px corners, condensed 600 type (22px for times, 16px for selects), 44 to 48 px tall. Focus is a 2 px motorway outline at 1 px offset; disabled fields go muted with a dotted border.

### Day chips
Seven equal cells with 4 px gaps, 44 px tall, condensed 14px. Off: hairline border, muted text, no fill. On: motorway fill, case border, motorway-ink text.

### Road gauge (signature)
The battery reading. A minor road across the section; a cased motorway (14 px casing, 10 px fill) from the start to the level; small junctions at 25, 50 and 75 % within the filled stretch; a 5.5 px ink-ringed junction at the head; a distance marker beneath with ink triangles at the start and the head, the RANGE label, the figure at 26px and the unit. Tone follows the Road Class Rule: motorway normally, green while charging (with white traffic chevrons flowing along it at 1.6 s per cycle), yellow at 20 % or below, red at 10 % or below.

### Day road
A 24-hour minor road with ticks every three hours (longer every six) and hour numerals at 00, 06, 12, 18, 24. The charging window is a motorway stretch with junctions at its ends; overnight windows wrap to both ends. A small ink triangle above marks now. A window not yet confirmed by the car is drawn dashed at reduced opacity.

### Temperature road
The scale from minimum to maximum as a minor road. Cabin is a junction; target is a ringed junction with an ink centre; the stretch between is a cased motorway while the A/C runs and a dashed motorway-case line when it does not. Outside temperature is an ink triangle with an "OUTSIDE n°" tick label.

### History road
The Activity card's timeline: a vertical minor road down a 22 px column, a state mark at each event set on a land-tint square so it breaks the road, time on the left in condensed tabular muted type, title and cause on the right.

### Car plan
A top-down line drawing per body style (hatch, saloon, SUV, coupé SUV, MPV with sliding doors), front at the top, drawn in ink on plan-body with plan-glass glazing. Open doors swing or slide open and open lids lift, filled B-road yellow and called out with a yellow triangle and an uppercase plan label, so state reads without colour. Tyre pressures sit in a four-cell row beneath; a pressure under the owner's warning level turns red-ink with a fault triangle.

### Command note and signature interaction
**A command in flight is a road under construction.** The control's border turns transparent, its face turns water and its text motorway-case, and a dashed motorway-case border (8 px period, 1.5 px thick) marches around it every 0.8 s. A note beneath with a dashed waiting ring says "Lock: waiting for the car". Confirmed, the dashes close back into a solid control and the note takes the green square. Refused, the control takes the A-road red border and the note turns red-ink with the fault triangle and the car's own reason. Not confirmed in time takes the yellow triangle. Under reduced motion the dashes stay still and the charging chevrons stop.

## Do's and Don'ts

### Do:
- **Do** draw any reading that has length (a level, a span of time, a range of values, a sequence of choices) as a cased road with junctions, sized to the section's measured width.
- **Do** pick road colour by meaning only: motorway for state or selection, green for healthy or charging, red for fault or refusal, yellow for warning or open.
- **Do** case every coloured fill with its own case token, and use the night-atlas values through the same token names.
- **Do** pair every state colour with its mark shape: square, triangle, dashed ring, open square.
- **Do** set every changing number in Barlow Condensed with tabular figures, and name it with a 12px uppercase label.
- **Do** keep controls on paper with an edge border and 2px corners, at least 44 px tall, 48 px for primary actions.
- **Do** show a pending command with the marching dashed casing, and keep motion to state changes of 150 to 250 ms (the march and the charging flow are the only loops), stilled under reduced motion.
- **Do** require a 700 ms hold for consequential actions (unlock, open boot, turn off, release the cable).
- **Do** respond to the card's container width (380 px and 330 px steps), not the viewport.

### Don't:
- **Don't** use dark glass tiles, a hero car render, or a ring gauge; this world refuses that category default.
- **Don't** add drop shadows, blur or layered surfaces; the card is flat land tint with a hairline border.
- **Don't** introduce colours outside the road classes and neutrals, or use a road colour for decoration.
- **Don't** use rounded pill controls or large radii; corners stop at 4px on cards and 2px on controls.
- **Don't** let colour alone carry a state.
- **Don't** set uppercase labels above a heading as decoration; a label names a value.
- **Don't** fetch fonts or other assets from third parties at runtime, or use GAC artwork.

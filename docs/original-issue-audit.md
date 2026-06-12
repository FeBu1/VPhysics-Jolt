# Original VPhysics-Jolt issue audit

This document tracks compatibility and regression areas copied from the original `misyltoad/VPhysics-Jolt` issue tracker and compares them against this fork's current `fixed` branch.

Generated from issue/code inspection on 2026-06-12.

## High-priority still relevant

### LVS / simfphys / GLIDE style vehicle addon compatibility

Relevant original issues:

- misyltoad/VPhysics-Jolt#50 - LFS / stool doors / simfphys weird behavior
- misyltoad/VPhysics-Jolt#255 - LVS / simfphys wheels fly up / vehicles launch
- misyltoad/VPhysics-Jolt#256 - GLIDE vehicles spin like crazy
- misyltoad/VPhysics-Jolt#264 - GLIDE almost works but spins
- misyltoad/VPhysics-Jolt#275 - simfphys / vehicle bases stuck/spazzing
- RaphaelIT7/VPhysics-Jolt#19 - LVS vehicles stuck, levitated, immovable

Current finding:

- This fork still logs the `ragdoll.onlyAngularLimits` warning in `JoltPhysicsConstraint::InitialiseRagdoll` and does not implement angular-only ragdoll constraints.
- This likely explains LVS vehicles freezing/levitating because a constraint that should only limit rotation can still constrain translation.

Recommended fix:

- Add an `onlyAngularLimits` path using `JPH::SixDOFConstraintSettings`.
- Free `TranslationX/Y/Z`.
- Limit or fix `RotationX/Y/Z` using the existing Source ragdoll axis limits.
- Keep normal ragdolls on the existing fixed/hinge/swing-twist path.

Status: **needs code patch + in-game testing**.

### Vehicle suspension / wheel tuning

Relevant issues:

- RaphaelIT7/VPhysics-Jolt#18 - Vehicle suspension too soft?
- misyltoad/VPhysics-Jolt#50
- misyltoad/VPhysics-Jolt#255
- misyltoad/VPhysics-Jolt#275

Current finding:

- Current vehicle code multiplies Source suspension spring/damping by body mass before feeding Jolt stiffness/damping.
- There is no legacy/IVP compatibility ConVar for suspension scaling yet.
- `SetSpringLength` is currently empty.

Recommended fix:

- Add compatibility ConVars for suspension stiffness/damping scale.
- Implement `SetSpringLength` if Source/GMod vehicle code expects runtime changes.
- Build a small test matrix: Jeep, Jalopy, Airboat, LVS wheeled, simfphys, GLIDE.

Status: **likely still needs work**.

### Collision speed / addon callback compatibility

Relevant issues:

- RaphaelIT7/VPhysics-Jolt#17 - Collision speed calculation is wrong?
- misyltoad/VPhysics-Jolt#255 - gore mods/ragdoll damage weirdness
- old prop damage / impact / callback reports

Current finding:

- Current contact listener computes `collisionSpeed` in `FlushCallbacks` from post-resolution velocities projected onto the collision normal.
- It fakes linear velocities during `PreCollision` to preserve old/new velocity deltas.
- This is explicitly compatibility-oriented, but the open issue suggests addons still see mismatches.

Recommended fix:

- Add a `vjolt_legacy_collision_speed` compatibility mode.
- Track and expose both pre-solver and post-solver relative normal speed.
- Compare GMod `colData.OurOldVelocity`, `OurNewVelocity`, `TheirOldVelocity`, `TheirNewVelocity`, and `HitSpeed` against IVP.

Status: **partially addressed, needs compatibility mode/testing**.

### Buoyancy / water

Relevant issues:

- RaphaelIT7/VPhysics-Jolt#15 - heavy objects float in water
- misyltoad/VPhysics-Jolt#133 - standing on objects in water launches player
- misyltoad/VPhysics-Jolt#64 - Gwater does not work

Current finding:

- Upstream maintainer comment says buoyancy is simplified and needs rework.
- Water/player/object interactions remain high risk.

Recommended fix:

- Audit `vjolt_controller_fluid.cpp`.
- Add volume/mass/submerged-depth sanity clamps.
- Add legacy buoyancy mode if changing default behavior is too risky.

Status: **needs investigation**.

### Portals / backfaces

Relevant issues:

- misyltoad/VPhysics-Jolt#8
- misyltoad/VPhysics-Jolt#160
- misyltoad/VPhysics-Jolt#283 - Broken Portals

Current finding:

- Current trace code still has portal/backface hacks and force-backface ConVars.
- This looks not fully solved; it is managed by toggles/hacks.

Recommended fix:

- Re-test Portal/Portal 2 brush/trigger traces.
- Isolate whether bad winding, backface policy, or convex-vs-triangle trace mode is the real cause.

Status: **likely still open**.

## Appears fixed / mitigated in this fork

### Player gets stuck walking over props / vphysics stairs

Relevant issues:

- misyltoad/VPhysics-Jolt#72 - vphysics stairs inconsistent
- misyltoad/VPhysics-Jolt#234 - player stuck when walking over props
- misyltoad/VPhysics-Jolt#279 - cannot walk on stairs in GMod

Current finding:

- `CastBoxVsShape` leaves `settings.mUseShrunkenShapeAndConvexRadius` disabled with a note saying it caused false collision detection.
- This matches the known workaround from #234.

Status: **mitigated, still needs stair regression test**.

### Springs/constraints deleted while objects are destroyed

Relevant issues:

- misyltoad/VPhysics-Jolt#85 - props destroyed while connected to expanding hydraulic crash
- misyltoad/VPhysics-Jolt#137 - hard crash when cable/constraint detached/destroyed

Current finding:

- `JoltPhysicsSpring::OnJoltPhysicsObjectDestroyed` removes the Jolt constraint immediately and nulls it.
- Environment constraint deletion queues constraints during simulation.

Status: **likely fixed/mitigated**.

### No-collide still physically colliding

Relevant issue:

- misyltoad/VPhysics-Jolt#107 - no-collide pairs still interact, affecting LFS/simfphys

Current finding:

- Contact listener calls game `ShouldCollide`.
- Non-colliding pairs are set as sensors through `ioSettings.mIsSensor`, preserving touch callbacks without physical collision.
- There is a cached `ShouldCollide` path to avoid unsafe/expensive Lua/game callbacks from worker threads.

Status: **likely fixed, but cache invalidation should be watched**.

### Debug/access-violation and build compatibility fixes

Relevant commits/issues:

- debug renderer shutdown fixes
- SSE/AVX flag leakage fixes
- SDK compatibility fixes around `MatrixAxisType_t` / `VectorAbs`

Current finding:

- The fork includes recent workflow/build fixes and newer compatibility code.

Status: **likely integrated**.

## Suggested next branch work

1. Implement angular-only ragdoll constraints for LVS.
2. Add compatibility ConVars for vehicle suspension scale.
3. Add legacy collision-speed mode for GMod addon callbacks.
4. Audit fluid/buoyancy controller and add safer mass/volume/submerged clamps.
5. Re-test portal trace/backface behavior.

## Test matrix

Minimum manual tests before merging:

- Spawn default Jeep/Jalopy/Airboat.
- Spawn LVS wheeled and flying vehicle.
- Spawn simfphys/TDM/GLIDE vehicles.
- Spawn ragdolls with gore/ragdoll mods.
- Use no-collide tool on fast moving props.
- Destroy props connected to hydraulics/ropes/springs.
- Walk over physics stairs/props.
- Test water with heavy props and player standing on floating props.
- Test Portal/Portal 2 portal-trigger traces.

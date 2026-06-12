#!/usr/bin/env python3
"""Apply ChatGPT compatibility fixes to local Volt source files.

Run from the repository root:

    python tools/apply_chatgpt_compat_fixes.py
    git diff

This avoids risky full-file replacement through the GitHub connector for very
large C++ files.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS_CPP = ROOT / "vphysics_jolt" / "vjolt_constraints.cpp"
VEHICLE_CPP = ROOT / "vphysics_jolt" / "vjolt_controller_vehicle.cpp"
FLUID_CPP = ROOT / "vphysics_jolt" / "vjolt_controller_fluid.cpp"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"{label}: start marker not found")

    end_index = text.find(end, start_index)
    if end_index < 0:
        raise RuntimeError(f"{label}: end marker not found")

    return text[:start_index] + replacement + text[end_index:]


def patch_constraints(text: str) -> str:
    if "Some Garry's Mod vehicle bases, notably LVS" not in text:
        start = "\tJPH::Constraint *pConstraint = nullptr;\n"
        end = "\n\tconst bool bActive = !m_pGroup && ragdoll.constraint.isActive;\n"

        replacement = """\tJPH::Constraint *pConstraint = nullptr;\n\n\tif ( ragdoll.onlyAngularLimits )\n\t{\n\t\t// Some Garry's Mod vehicle bases, notably LVS, use ragdoll constraints as\n\t\t// angular limit helpers. IVP/VPhysics leaves the linear axes unconstrained in\n\t\t// this mode; constraining translation here pins or levitates vehicles.\n\t\tJPH::SixDOFConstraintSettings settings;\n\t\tsettings.mSpace = JPH::EConstraintSpace::LocalToBodyCOM;\n\t\tsettings.mSwingType = JPH::ESwingType::Pyramid;\n\n\t\tsettings.mPosition1 = constraintToReference.GetTranslation() - pRefBody->GetShape()->GetCenterOfMass();\n\t\tsettings.mAxisX1 = constraintToReference.GetAxisX();\n\t\tsettings.mAxisY1 = constraintToReference.GetAxisY();\n\n\t\tsettings.mPosition2 = constraintToAttached.GetTranslation() - pAttBody->GetShape()->GetCenterOfMass();\n\t\tsettings.mAxisX2 = constraintToAttached.GetAxisX();\n\t\tsettings.mAxisY2 = constraintToAttached.GetAxisY();\n\n\t\tsettings.MakeFreeAxis( JPH::SixDOFConstraintSettings::TranslationX );\n\t\tsettings.MakeFreeAxis( JPH::SixDOFConstraintSettings::TranslationY );\n\t\tsettings.MakeFreeAxis( JPH::SixDOFConstraintSettings::TranslationZ );\n\n\t\tfor ( int i = 0; i < 3; ++i )\n\t\t{\n\t\t\tconst JPH::SixDOFConstraintSettings::EAxis eRotAxis = JPH::SixDOFConstraintSettings::EAxis( JPH::SixDOFConstraintSettings::RotationX + i );\n\t\t\tif ( limits.lAxisLimitsRad[i].GetRange() > DEG2RAD( 0.1f ) )\n\t\t\t\tsettings.SetLimitedAxis( eRotAxis, limits.lAxisLimitsRad[i].Min, limits.lAxisLimitsRad[i].Max );\n\t\t\telse\n\t\t\t\tsettings.MakeFixedAxis( eRotAxis );\n\n\t\t\tsettings.mMaxFriction[ eRotAxis ] = Max( flMinTorqueFriction, SourceToJolt::Torque( ragdoll.axes[i].torque ) );\n\t\t}\n\n\t\tpConstraint = settings.Create( *pRefBody, *pAttBody );\n\t}\n\telse if ( uDOFCount == 0 )\n\t{\n\t\tJPH::FixedConstraintSettings settings;\n\t\tsettings.mAutoDetectPoint = true;\n\n\t\tpConstraint = settings.Create( *pRefBody, *pAttBody );\n\t}\n\telse if ( uDOFCount == 1 )\n\t{\n\t\tJoltMatrixAxes eAxis = *DOFBitToAxis( uDOFMask );\n\n\t\tJPH::HingeConstraintSettings settings;\n\t\tsettings.mPoint1 = SourceToJolt::Distance( GetColumn( constraintToWorld, MatrixAxis::Origin ) );\n\t\tsettings.mPoint2 = SourceToJolt::Distance( GetColumn( constraintToWorld, MatrixAxis::Origin ) );\n\t\tsettings.mHingeAxis1 = SourceToJolt::Unitless( GetColumn( constraintToWorld, eAxis ) );\n\t\tsettings.mHingeAxis2 = SourceToJolt::Unitless( GetColumn( constraintToWorld, eAxis ) );\n\t\tsettings.mNormalAxis1 = HingePerpendicularVector( settings.mHingeAxis1 );\n\t\tsettings.mNormalAxis2 = HingePerpendicularVector( settings.mHingeAxis2 );\n\t\tsettings.mLimitsMin = limits.lAxisLimitsRad[ eAxis ].Min;\n\t\tsettings.mLimitsMax = limits.lAxisLimitsRad[ eAxis ].Max;\n\t\tsettings.mMaxFrictionTorque = Max( flMinTorqueFriction, SourceToJolt::Torque( ragdoll.axes[ eAxis ].torque ) );\n\n\t\tpConstraint = settings.Create( *pRefBody, *pAttBody );\n\t}\n\telse\n\t{\n\t\tJPH::SwingTwistConstraintSettings settings;\n\t\t// Allow ~1deg either side to avoid joints glitching out.\n\t\tsettings.mTwistMinAngle = Min( limits.lAxisLimitsRad[0].Min, DEG2RAD( -1.0f ) );\n\t\tsettings.mTwistMaxAngle = Max( limits.lAxisLimitsRad[0].Max, DEG2RAD(  1.0f ) );\n\t\tsettings.mNormalHalfConeAngle = Max( 0.5f * ( limits.lAxisLimitsRad[1].GetRange() ), DEG2RAD( 1.0f ) );\n\t\tsettings.mPlaneHalfConeAngle = Max( 0.5f * ( limits.lAxisLimitsRad[2].GetRange() ), DEG2RAD( 1.0f ) );\n\n\t\tsettings.mSpace = JPH::EConstraintSpace::LocalToBodyCOM;\n\n\t\tsettings.mPosition1 = constraintToReference.GetTranslation() - pRefBody->GetShape()->GetCenterOfMass();\n\t\tsettings.mTwistAxis1 = constraintToReference.GetAxisX();\n\t\tsettings.mPlaneAxis1 = constraintToReference.GetAxisY();\n\n\t\tsettings.mPosition2 = constraintToAttached.GetTranslation() - pAttBody->GetShape()->GetCenterOfMass();\n\t\tsettings.mTwistAxis2 = constraintToAttached.GetAxisX();\n\t\tsettings.mPlaneAxis2 = constraintToAttached.GetAxisY();\n\n\t\tsettings.mMaxFrictionTorque = Max( flMinTorqueFriction, SourceToJolt::Torque( ( ragdoll.axes[0].torque + ragdoll.axes[1].torque + ragdoll.axes[2].torque ) / 3.0f ) );\n\n\t\tpConstraint = settings.Create( *pRefBody, *pAttBody );\n\t}\n"""
        text = replace_between(text, start, end, replacement, "LVS angular-only constraints")

    if "EConstraintSubType::SixDOF" not in text[text.find("static void GetConstraintImpulses"):]:
        old = """\t\tcase JPH::EConstraintSubType::Pulley:\n\t\t{\n\t\t\tauto *p = static_cast< const JPH::PulleyConstraint * >( pConstraint );\n\t\t\toutLinear = fabsf( p->GetTotalLambdaPosition() );\n\t\t\tbreak;\n\t\t}\n\t\tdefault:\n"""
        new = """\t\tcase JPH::EConstraintSubType::Pulley:\n\t\t{\n\t\t\tauto *p = static_cast< const JPH::PulleyConstraint * >( pConstraint );\n\t\t\toutLinear = fabsf( p->GetTotalLambdaPosition() );\n\t\t\tbreak;\n\t\t}\n\t\tcase JPH::EConstraintSubType::SixDOF:\n\t\t{\n\t\t\tauto *p = static_cast< const JPH::SixDOFConstraint * >( pConstraint );\n\t\t\toutLinear = p->GetTotalLambdaPosition().Length();\n\t\t\toutAngular = p->GetTotalLambdaRotation().Length();\n\t\t\tbreak;\n\t\t}\n\t\tdefault:\n"""
        text = replace_once(text, old, new, "SixDOF impulse reporting")

    return text


def patch_vehicle(text: str) -> str:
    if "vjolt_vehicle_suspension_stiffness_scale" not in text:
        old = 'static ConVar vjolt_vehicle_throttle_override( "vjolt_vehicle_throttle_override", "-1.0", FCVAR_NONE );\n\nstatic ConVar vjolt_airboat_debug'
        new = 'static ConVar vjolt_vehicle_throttle_override( "vjolt_vehicle_throttle_override", "-1.0", FCVAR_NONE );\n\nstatic ConVar vjolt_vehicle_suspension_stiffness_scale( "vjolt_vehicle_suspension_stiffness_scale", "1.0", FCVAR_NONE,\n\t"Scales Source vehicle suspension spring stiffness before passing it to Jolt. Compatibility/tuning aid for vehicle bases." );\nstatic ConVar vjolt_vehicle_suspension_damping_scale( "vjolt_vehicle_suspension_damping_scale", "1.0", FCVAR_NONE,\n\t"Scales Source vehicle suspension damping before passing it to Jolt. Compatibility/tuning aid for vehicle bases." );\n\nstatic ConVar vjolt_airboat_debug'
        text = replace_once(text, old, new, "vehicle suspension scale ConVars")

    old = """\twheelSettings->mSuspensionSpring.mStiffness = axle.suspension.springConstant * m_pCarBodyObject->GetMass();\n\twheelSettings->mSuspensionSpring.mDamping = axle.suspension.springDamping * m_pCarBodyObject->GetMass();\n"""
    new = """\twheelSettings->mSuspensionSpring.mStiffness = axle.suspension.springConstant * m_pCarBodyObject->GetMass() * vjolt_vehicle_suspension_stiffness_scale.GetFloat();\n\twheelSettings->mSuspensionSpring.mDamping = axle.suspension.springDamping * m_pCarBodyObject->GetMass() * vjolt_vehicle_suspension_damping_scale.GetFloat();\n"""
    if old in text:
        text = replace_once(text, old, new, "vehicle suspension scale usage")

    return text


def patch_fluid(text: str) -> str:
    if "vjolt_fluid_buoyancy_scale" not in text:
        old = "//-------------------------------------------------------------------------------------------------\n\n// Josh: The surfacePlane"
        new = """//-------------------------------------------------------------------------------------------------\n\nstatic ConVar vjolt_fluid_buoyancy_scale( \"vjolt_fluid_buoyancy_scale\", \"1.0\", FCVAR_NONE,\n\t\"Scales buoyancy impulse strength. Compatibility/tuning aid for heavy objects and water addons.\" );\nstatic ConVar vjolt_fluid_buoyancy_max_ratio( \"vjolt_fluid_buoyancy_max_ratio\", \"1.0\", FCVAR_NONE,\n\t\"Caps Jolt buoyancy ratio. 0 disables the cap; 1 roughly prevents stronger-than-neutral buoyancy.\" );\n\n// Josh: The surfacePlane"""
        text = replace_once(text, old, new, "fluid buoyancy ConVars")

    old = """\t\tfloat inBuoyancy = flFluidDensity * pObject->GetBody()->GetShape()->GetVolume() * pObject->GetInvMass();\n\t\tif ( body.IsActive() )\n"""
    new = """\t\tfloat inBuoyancy = flFluidDensity * pObject->GetBody()->GetShape()->GetVolume() * pObject->GetInvMass();\n\t\tinBuoyancy *= vjolt_fluid_buoyancy_scale.GetFloat();\n\n\t\tconst float flMaxBuoyancyRatio = vjolt_fluid_buoyancy_max_ratio.GetFloat();\n\t\tif ( flMaxBuoyancyRatio > 0.0f )\n\t\t\tinBuoyancy = Min( inBuoyancy, flMaxBuoyancyRatio );\n\n\t\tif ( body.IsActive() )\n"""
    if old in text:
        text = replace_once(text, old, new, "fluid buoyancy clamp")

    return text


def patch_file(path: Path, patcher) -> bool:
    text = path.read_text(encoding="utf-8")
    patched = patcher(text)
    if patched == text:
        print(f"No changes needed: {path.relative_to(ROOT)}")
        return False
    path.write_text(patched, encoding="utf-8", newline="\n")
    print(f"Updated: {path.relative_to(ROOT)}")
    return True


def main() -> None:
    changed = False
    changed |= patch_file(CONSTRAINTS_CPP, patch_constraints)
    changed |= patch_file(VEHICLE_CPP, patch_vehicle)
    changed |= patch_file(FLUID_CPP, patch_fluid)

    if not changed:
        print("No source changes needed.")
        return

    print("Review with:")
    print("  git diff -- vphysics_jolt/vjolt_constraints.cpp vphysics_jolt/vjolt_controller_vehicle.cpp vphysics_jolt/vjolt_controller_fluid.cpp")


if __name__ == "__main__":
    main()

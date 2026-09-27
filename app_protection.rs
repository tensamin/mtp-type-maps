use mtp::codec::{ApplicationProtectionPurpose, ProtectionPurpose};

pub const REGISTRATION_ACTIVATION: u8 = 0x71;
pub const PASSWORD_MANAGEMENT_SIGNATURE: u8 = 0x72;
pub const PASSWORD_MANAGEMENT_ENCRYPTION: u8 = 0x73;
pub const PASSWORD_RESPONSE_SIGNATURE: u8 = 0x74;
pub const PASSWORD_RESPONSE_ENCRYPTION: u8 = 0x75;
pub const PROVISIONING_CREDENTIAL_SIGNATURE: u8 = 0x76;
pub const PROVISIONING_CREDENTIAL_ENCRYPTION: u8 = 0x77;

pub fn purpose(value: u8) -> ProtectionPurpose {
    ApplicationProtectionPurpose::new(value)
        .expect("Tensamin application protection purpose must not be MTP-reserved")
        .into()
}

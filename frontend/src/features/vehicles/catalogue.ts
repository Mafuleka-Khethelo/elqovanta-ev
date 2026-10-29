// Model-name suggestions are not battery specifications. Never infer a pack
// from a model name alone. Only the exact sourced variants below prefill specs.
export const models = [
  "Audi Q4 e-tron", "Audi Q6 e-tron", "Audi Q8 e-tron", "Audi e-tron GT",
  "BMW i3", "BMW i3s", "BMW i4", "BMW i5", "BMW i7", "BMW iX", "BMW iX1", "BMW iX2", "BMW iX3",
  "BYD ATTO 3", "BYD DOLPHIN", "BYD SEAL", "BYD SEALION 7",
  "Chevrolet Bolt EV", "Chevrolet Bolt EUV", "Citroën ë-C4", "Fiat 500e",
  "Ford Mustang Mach-E", "Ford F-150 Lightning", "GWM ORA 03",
  "Honda e", "Hyundai IONIQ 5", "Hyundai IONIQ 6", "Hyundai KONA Electric",
  "Jaguar I-PACE", "Kia EV3", "Kia EV6", "Kia EV9", "Kia Niro EV",
  "Lexus RZ", "Lucid Air", "Mazda MX-30", "Mercedes-Benz EQA", "Mercedes-Benz EQB",
  "Mercedes-Benz EQC", "Mercedes-Benz EQE", "Mercedes-Benz EQS", "MG4 Electric", "MG ZS EV",
  "MINI Cooper Electric", "Nissan ARIYA", "Nissan LEAF", "Opel Corsa Electric", "Peugeot e-208",
  "Polestar 2", "Polestar 3", "Porsche Taycan", "Renault ZOE", "Renault Megane E-Tech",
  "Rivian R1S", "Rivian R1T", "Smart #1", "Tesla Model 3", "Tesla Model S", "Tesla Model X", "Tesla Model Y",
  "Toyota bZ4X", "Volkswagen ID.3", "Volkswagen ID.4", "Volkswagen ID.5", "Volkswagen ID.7",
  "Volvo C40 Recharge", "Volvo EX30", "Volvo EX40", "Volvo XC40 Recharge",
].sort();

type Variant = { model: string; version: string; capacity: number; ac: number | null; dc: number | null; source: string };
const vw = "https://www.volkswagen.co.uk/idhub/content/dam/onehub_pkw/importers/gb/downloads/brochures/used-cars/id-3/id-3-brochure-pricelist-dec-20.pdf";
const bmw = "https://www.press.bmwgroup.com/usa/article/detail/T0285420EN_US/the-new-2019-bmw-i3-120ah-and-i3s-120ah";
export const variants: Variant[] = [
  { model: "Volkswagen ID.3", version: "2020 UK Pro Performance 58 kWh", capacity: 58, ac: 11, dc: 100, source: vw },
  { model: "Volkswagen ID.3", version: "2020 UK Pro S 77 kWh", capacity: 77, ac: 11, dc: 125, source: vw },
  // BMW's US press table has inconsistent AC labels; do not prefill an AC limit.
  { model: "BMW i3", version: "2019 US 120 Ah", capacity: 37.9, ac: null, dc: 50, source: bmw },
  { model: "BMW i3s", version: "2019 US 120 Ah", capacity: 37.9, ac: null, dc: 50, source: bmw },
];

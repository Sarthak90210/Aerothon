import type { Dimensions, DimensionField } from "./types";

export function validateDraft(
  values: Dimensions,
  fields: DimensionField[],
): string[] {
  const errors: string[] = [];
  for (const f of fields) {
    const n = values[f.group]?.[f.key];
    if (typeof n !== "number" || !Number.isFinite(n) || n < f.min || n > f.max)
      errors.push(
        `${f.label}: enter ${f.min}–${f.max} ${f.key.endsWith("_m") ? "m" : "kg"}`,
      );
  }
  if (
    !["suspended", "ground", "both"].includes(String(values.banner?.placement))
  )
    errors.push("Select a banner placement");
  if (!["right", "left"].includes(String(values.corridor?.return_side)))
    errors.push("Select a return lane side");
  const c = values.corridor,
    b = values.banner;
  if (Number(c?.nav_height_m) >= Number(c?.wall_height_m))
    errors.push("Navigation height must be below corridor walls");
  if (Number(c?.nav_height_m) >= Number(values.hall?.ceiling_m))
    errors.push("Navigation height must be below the hall ceiling");
  if (Number(c?.spacing_m) < Number(c?.width_m))
    errors.push("Corridor spacing must be at least the corridor width");
  if (
    2 * Number(b?.border_m) >=
    Math.min(
      Number(b?.width_m),
      Number(b?.height_m),
      Number(b?.ground_height_m ?? b?.height_m),
    )
  )
    errors.push("Banner border leaves no coloured panel");
  // Same rule as arena_dimensions.validate: the lidar plane (0.0815 m above
  // the body) stays 0.1 m under the obstacle tops, or it cannot see them.
  const obstacleTop = Number(values.obstacle?.height_m);
  if (
    Number.isFinite(obstacleTop) &&
    Number(c?.nav_height_m) + 0.0815 > obstacleTop - 0.1
  )
    errors.push(
      `Navigation height must be ${(obstacleTop - 0.1815).toFixed(2)} m or less so the lidar sees the obstacles`,
    );
  return errors;
}

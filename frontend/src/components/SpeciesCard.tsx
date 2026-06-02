import { Card, CardContent, CardMedia, Chip, Stack, Typography } from "@mui/material";

import type { PlantSpecies } from "../types/api";

const lightLabel: Record<string, string> = {
  low: "Тень",
  medium: "Рассеянный свет",
  high: "Яркий свет",
};

export function SpeciesCard({ species }: { species: PlantSpecies }) {
  return (
    <Card sx={{ height: "100%", overflow: "hidden" }}>
      {species.image_url && <CardMedia component="img" image={species.image_url} height="170" alt={species.name} />}
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" gap={1}>
            <Typography variant="h6">{species.name}</Typography>
            <Chip size="small" label={`${species.watering_interval_days} дн.`} color="primary" variant="outlined" />
          </Stack>
          <Typography variant="body2" color="text.secondary" fontStyle="italic">
            {species.latin_name || "латинское название не указано"}
          </Typography>
          <Typography variant="body2">{species.description}</Typography>
          <Stack direction="row" gap={1} flexWrap="wrap">
            <Chip size="small" label={lightLabel[species.light]} />
            <Chip size="small" label={`Влажность ${species.humidity}%`} />
            {species.pet_safe && <Chip size="small" label="Безопасно для питомцев" color="success" />}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

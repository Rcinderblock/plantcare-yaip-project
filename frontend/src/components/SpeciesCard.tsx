import SpaIcon from "@mui/icons-material/Spa";
import { Box, Card, CardContent, CardMedia, Chip, Stack, Typography } from "@mui/material";
import { useState } from "react";

import type { PlantSpecies } from "../types/api";

const lightLabel: Record<string, string> = {
  low: "Тень",
  medium: "Рассеянный свет",
  high: "Яркий свет",
};

export function SpeciesCard({ species }: { species: PlantSpecies }) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = species.image_url && !imageFailed;

  return (
    <Card sx={{ height: "100%", overflow: "hidden" }}>
      {showImage ? (
        <CardMedia component="img" image={species.image_url} height="170" alt={species.name} onError={() => setImageFailed(true)} />
      ) : (
        <Box
          sx={{
            alignItems: "center",
            bgcolor: "primary.light",
            color: "primary.contrastText",
            display: "flex",
            height: 170,
            justifyContent: "center",
          }}
        >
          <Stack alignItems="center" spacing={1}>
            <SpaIcon sx={{ fontSize: 54 }} />
            <Typography fontWeight={700}>{species.name}</Typography>
          </Stack>
        </Box>
      )}
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

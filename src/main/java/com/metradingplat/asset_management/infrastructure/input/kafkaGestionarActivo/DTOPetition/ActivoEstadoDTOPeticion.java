package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.DTOPetition;

import java.time.LocalDateTime;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@AllArgsConstructor
@NoArgsConstructor
public class ActivoEstadoDTOPeticion {
    private Long idEscaner;
    private String nombreEscaner;
    private String symbol;
    private String estado;
    private String metadatos;
    private LocalDateTime timestamp;
}

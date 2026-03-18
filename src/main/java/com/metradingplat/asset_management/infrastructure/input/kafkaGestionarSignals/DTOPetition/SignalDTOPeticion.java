package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.DTOPetition;

import java.time.LocalDateTime;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class SignalDTOPeticion {
    private Long idEscaner;
    private String nombreEscaner;
    private String symbol;
    private String tipoSenal;
    private String filtrosAplicados;
    private Double precioDeteccion;
    private Long volumenDeteccion;
    private LocalDateTime timestamp;
}

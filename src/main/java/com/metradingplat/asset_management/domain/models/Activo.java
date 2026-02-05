package com.metradingplat.asset_management.domain.models;

import java.time.LocalDateTime;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class Activo {
    private Long idActivo;
    private Long idEscaner;
    private String nombreEscaner;
    private String symbol;
    private String estado;
    private LocalDateTime fechaDeteccion;
    private LocalDateTime fechaActualizacion;
    private String metadatos;
}

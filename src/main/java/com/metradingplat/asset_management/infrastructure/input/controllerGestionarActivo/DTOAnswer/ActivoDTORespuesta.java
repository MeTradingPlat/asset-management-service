package com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.DTOAnswer;

import java.time.LocalDateTime;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@AllArgsConstructor
@NoArgsConstructor
public class ActivoDTORespuesta {
    private Long idActivo;
    private Long idEscaner;
    private String nombreEscaner;
    private String symbol;
    private String estado;
    private LocalDateTime fechaDeteccion;
    private LocalDateTime fechaActualizacion;
    private String metadatos;
}

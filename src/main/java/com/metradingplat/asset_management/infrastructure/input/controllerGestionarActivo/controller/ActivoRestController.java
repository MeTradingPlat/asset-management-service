package com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.controller;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.metradingplat.asset_management.application.input.GestionarActivoCUIntPort;
import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.DTOAnswer.ActivoDTORespuesta;
import com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.mapper.ActivoMapperInfraestructuraDominio;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/activos")
@RequiredArgsConstructor
@Validated
public class ActivoRestController {

    private final GestionarActivoCUIntPort objGestionarActivoCUInt;
    private final ActivoMapperInfraestructuraDominio objMapper;

    @GetMapping
    public ResponseEntity<List<ActivoDTORespuesta>> listar() {
        List<Activo> activos = this.objGestionarActivoCUInt.listar();
        List<ActivoDTORespuesta> respuesta = this.objMapper.mappearListaDeActivoARespuesta(activos);
        return ResponseEntity.ok(respuesta);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ActivoDTORespuesta> obtenerPorId(
            @PathVariable("id") @NotNull @Positive Long id) {
        Activo activo = this.objGestionarActivoCUInt.obtenerPorId(id);
        ActivoDTORespuesta respuesta = this.objMapper.mappearDeActivoARespuesta(activo);
        return ResponseEntity.ok(respuesta);
    }

    @GetMapping("/escaner/{idEscaner}")
    public ResponseEntity<List<ActivoDTORespuesta>> obtenerPorEscaner(
            @PathVariable("idEscaner") @NotNull @Positive Long idEscaner) {
        List<Activo> activos = this.objGestionarActivoCUInt.obtenerActivosPorEscaner(idEscaner);
        List<ActivoDTORespuesta> respuesta = this.objMapper.mappearListaDeActivoARespuesta(activos);
        return ResponseEntity.ok(respuesta);
    }

    @DeleteMapping("/escaner/{idEscaner}")
    public ResponseEntity<Void> eliminarPorEscaner(
            @PathVariable("idEscaner") @NotNull @Positive Long idEscaner) {
        this.objGestionarActivoCUInt.eliminarActivosPorEscaner(idEscaner);
        return ResponseEntity.noContent().build();
    }
}

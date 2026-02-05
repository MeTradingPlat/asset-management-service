package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.mappers;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.ReportingPolicy;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.DTOPetition.SignalDTOPeticion;

@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface SignalKafkaMapper {

    @Mapping(target = "metadatos", expression = "java(\"{\\\"tipoSenal\\\":\\\"\" + dto.getTipoSenal() + \"\\\",\\\"filtros\\\":\" + dto.getFiltrosAplicados() + \",\\\"precio\\\":\" + dto.getPrecioDeteccion() + \",\\\"volumen\\\":\" + dto.getVolumenDeteccion() + \"}\")")
    Activo deDTOADominio(SignalDTOPeticion dto);
}

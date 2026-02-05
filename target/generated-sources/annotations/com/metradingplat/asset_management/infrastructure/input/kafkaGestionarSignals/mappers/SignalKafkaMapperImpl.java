package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.mappers;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarSignals.DTOPetition.SignalDTOPeticion;
import javax.annotation.processing.Generated;
import org.springframework.stereotype.Component;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2026-02-04T22:45:32-0500",
    comments = "version: 1.5.5.Final, compiler: Eclipse JDT (IDE) 3.45.0.v20260128-0750, environment: Java 21.0.9 (Eclipse Adoptium)"
)
@Component
public class SignalKafkaMapperImpl implements SignalKafkaMapper {

    @Override
    public Activo deDTOADominio(SignalDTOPeticion dto) {
        if ( dto == null ) {
            return null;
        }

        Activo activo = new Activo();

        activo.setIdEscaner( dto.getIdEscaner() );
        activo.setNombreEscaner( dto.getNombreEscaner() );
        activo.setSymbol( dto.getSymbol() );

        activo.setMetadatos( "{\"tipoSenal\":\"" + dto.getTipoSenal() + "\",\"filtros\":" + dto.getFiltrosAplicados() + ",\"precio\":" + dto.getPrecioDeteccion() + ",\"volumen\":" + dto.getVolumenDeteccion() + "}" );

        return activo;
    }
}

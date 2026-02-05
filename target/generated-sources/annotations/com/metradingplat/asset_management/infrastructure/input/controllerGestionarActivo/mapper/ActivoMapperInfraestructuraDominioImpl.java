package com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.mapper;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.DTOAnswer.ActivoDTORespuesta;
import java.util.ArrayList;
import java.util.List;
import javax.annotation.processing.Generated;
import org.springframework.stereotype.Component;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2026-02-04T22:45:32-0500",
    comments = "version: 1.5.5.Final, compiler: Eclipse JDT (IDE) 3.45.0.v20260128-0750, environment: Java 21.0.9 (Eclipse Adoptium)"
)
@Component
public class ActivoMapperInfraestructuraDominioImpl implements ActivoMapperInfraestructuraDominio {

    @Override
    public ActivoDTORespuesta mappearDeActivoARespuesta(Activo activo) {
        if ( activo == null ) {
            return null;
        }

        ActivoDTORespuesta activoDTORespuesta = new ActivoDTORespuesta();

        activoDTORespuesta.setEstado( activo.getEstado() );
        activoDTORespuesta.setFechaActualizacion( activo.getFechaActualizacion() );
        activoDTORespuesta.setFechaDeteccion( activo.getFechaDeteccion() );
        activoDTORespuesta.setIdActivo( activo.getIdActivo() );
        activoDTORespuesta.setIdEscaner( activo.getIdEscaner() );
        activoDTORespuesta.setMetadatos( activo.getMetadatos() );
        activoDTORespuesta.setNombreEscaner( activo.getNombreEscaner() );
        activoDTORespuesta.setSymbol( activo.getSymbol() );

        return activoDTORespuesta;
    }

    @Override
    public List<ActivoDTORespuesta> mappearListaDeActivoARespuesta(List<Activo> activos) {
        if ( activos == null ) {
            return null;
        }

        List<ActivoDTORespuesta> list = new ArrayList<ActivoDTORespuesta>( activos.size() );
        for ( Activo activo : activos ) {
            list.add( mappearDeActivoARespuesta( activo ) );
        }

        return list;
    }
}

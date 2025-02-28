// Copyright (c) IAV  GmbH.
// Licensed under the MIT license.
// SPDX-License-Identifier: MIT

use wheelchair_digital_twin_model::car_v1;

use wheelchair_digital_twin_providers_common::constants::chariott::{
    INVEHICLE_DIGITAL_TWIN_SERVICE_COMMUNICATION_KIND,
    INVEHICLE_DIGITAL_TWIN_SERVICE_COMMUNICATION_REFERENCE, INVEHICLE_DIGITAL_TWIN_SERVICE_NAME,
    INVEHICLE_DIGITAL_TWIN_SERVICE_NAMESPACE, INVEHICLE_DIGITAL_TWIN_SERVICE_VERSION,
};
use wheelchair_digital_twin_providers_common::constants::{digital_twin_operation, digital_twin_protocol};
use wheelchair_digital_twin_providers_common::utils::discover_service_using_chariott;
use env_logger::{Builder, Target};
use interfaces::invehicle_digital_twin::v1::invehicle_digital_twin_client::InvehicleDigitalTwinClient;
use interfaces::invehicle_digital_twin::v1::{EndpointInfo, EntityAccessInfo, RegisterRequest};
use log::{debug, info, LevelFilter};
use wheelchair_assistant_interfaces::digital_twin_get_provider::v1::digital_twin_get_provider_server::DigitalTwinGetProviderServer;
use std::net::SocketAddr;
use tokio::signal;
use tonic::transport::Server;
use tonic::Status;
use car_on_provider_impl::CarOnProviderImpl;

mod car_on_provider_impl;

// TODO: These could be added in configuration
const CHARIOTT_SERVICE_DISCOVERY_URI: &str = "http://0.0.0.0:50000";
const PROVIDER_AUTHORITY: &str = "0.0.0.0:4030";

/// Register the "is_car_on" property's endpoint.
///
/// # Arguments
/// * `invehicle_digital_twin_uri` - The In-Vehicle Digital Twin URI.
/// * `provider_uri` - The provider's URI.
async fn register_entity(
    invehicle_digital_twin_uri: &str,
    provider_uri: &str,
) -> Result<(), Status> {
    let is_car_on_endpoint_info = EndpointInfo {
        protocol: digital_twin_protocol::GRPC.to_string(),
        operations: vec![digital_twin_operation::GET.to_string()],
        uri: provider_uri.to_string(),
        context: car_v1::car::is_car_running::ID.to_string(),
    };
    let entity_access_info = EntityAccessInfo {
        name: car_v1::car::is_car_running::NAME.to_string(),
        id: car_v1::car::is_car_running::ID.to_string(),
        description: car_v1::car::is_car_running::DESCRIPTION.to_string(),
        endpoint_info_list: vec![is_car_on_endpoint_info],
    };

    let mut client = InvehicleDigitalTwinClient::connect(invehicle_digital_twin_uri.to_string())
        .await
        .map_err(|e| Status::internal(e.to_string()))?;
    let request = tonic::Request::new(RegisterRequest {
        entity_access_info_list: vec![entity_access_info],
    });
    let _response = client.register(request).await?;

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Set up logging.
    Builder::new()
        .filter(None, LevelFilter::Debug)
        .target(Target::Stdout)
        .init();

    info!("The Provider CarOn has started.");

    let provider_uri = format!("http://{PROVIDER_AUTHORITY}");
    debug!("The Provider URI is {}", &provider_uri);

    // Setup the HTTP server.
    let addr: SocketAddr = PROVIDER_AUTHORITY.parse()?;
    let provider_impl = CarOnProviderImpl::default();
    let server_future = Server::builder()
        .add_service(DigitalTwinGetProviderServer::new(provider_impl))
        .serve(addr);
    info!("The HTTP server is listening on address '{PROVIDER_AUTHORITY}'");

    // Get the In-vehicle Digital Twin Uri from the service discovery system
    // This could be enhanced to add retries for robustness
    let invehicle_digital_twin_uri = discover_service_using_chariott(
        CHARIOTT_SERVICE_DISCOVERY_URI,
        INVEHICLE_DIGITAL_TWIN_SERVICE_NAMESPACE,
        INVEHICLE_DIGITAL_TWIN_SERVICE_NAME,
        INVEHICLE_DIGITAL_TWIN_SERVICE_VERSION,
        INVEHICLE_DIGITAL_TWIN_SERVICE_COMMUNICATION_KIND,
        INVEHICLE_DIGITAL_TWIN_SERVICE_COMMUNICATION_REFERENCE,
    )
    .await?;

    debug!("Sending a register request to the In-Vehicle Digital Twin Service URI {invehicle_digital_twin_uri}");

    // This could be enhanced to add retries for robustness
    register_entity(&invehicle_digital_twin_uri, &provider_uri).await?;
    server_future.await?;

    signal::ctrl_c()
        .await
        .expect("Failed to listen for control-c event");

    info!("The Provider has completed.");

    Ok(())
}

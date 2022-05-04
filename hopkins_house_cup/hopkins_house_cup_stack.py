from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
    aws_lambda as _lambda,
    aws_dynamodb as dynamo_db,
    aws_s3_assets as assets,
    alexa_ask
)
import aws_cdk as cdk

from aws_cdk.aws_iam import (
    ServicePrincipal,
    Role,
    PolicyStatement,
    CompositePrincipal
)
import aws_cdk.aws_route53 as route53
import aws_cdk.aws_cloudfront as cloudfront
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_iam as iam
import aws_cdk.aws_certificatemanager as acm
from aws_cdk.aws_cloudfront_origins import (
  S3Origin
)
from aws_cdk.aws_route53_targets import (
  CloudFrontTarget,
  Route53RecordTarget
)
import aws_cdk.aws_s3_deployment as s3deploy

import subprocess
import os

from constructs import Construct


class HopkinsHouseCupStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Must register this in Route53
        domain_name = 'hopkinshousecup.com'

        # Requires you own the domain name passed as param and hosted zone exists in R53
        zone = route53.HostedZone.from_lookup(self, 'HouseCupZone', domain_name=domain_name);

        # Create Origin Access Identity
        cloudfront_OAI = cloudfront.OriginAccessIdentity(self, 'cloudfront-OAI', comment=f"OAI for {id}")
        CfnOutput(self, "HopkinsOAI", value=f"https://{domain_name}")

        # S3 site content bucket
        site_bucket = s3.Bucket(self, 'HouseCupBucket', 
          bucket_name=domain_name,
          public_read_access=False,
          block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
          removal_policy=RemovalPolicy.DESTROY,
          auto_delete_objects=True
        )
        
        # Grant S3 bucket access to CloudFront
        site_bucket.add_to_resource_policy(iam.PolicyStatement(
          actions=['s3:GetObject'],
          resources=[site_bucket.arn_for_objects('*')],
          principals=[iam.CanonicalUserPrincipal(cloudfront_OAI.cloud_front_origin_access_identity_s3_canonical_user_id)]
        ))
        CfnOutput(self, "HouseBucket", value=site_bucket.bucket_name)

        # TLS certificate for use with website
        certificate = acm.DnsValidatedCertificate(self, 'HopkinsHouseCupCertificate',
          domain_name=domain_name,
          subject_alternative_names=[
            '*.' + domain_name
          ],
          hosted_zone=zone,
          region='us-east-1', 
        )
        CfnOutput(self, 'Certificate', value=certificate.certificate_arn)
        
        # CloudFront distribution instantiation
        s3_origin = S3Origin(site_bucket, origin_access_identity=cloudfront_OAI)
        distribution = cloudfront.Distribution(self, 'HopkinsHouseCupDistribution',
          certificate=certificate,
          default_root_object="index.html",
          domain_names=[
            domain_name, 
            f"*.{domain_name}" 
          ],
          minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
          default_behavior=cloudfront.BehaviorOptions(
            origin=s3_origin,
            compress=True,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
          ),
          geo_restriction=cloudfront.GeoRestriction.denylist('RU', 'SG', 'AE')
        )
        CfnOutput(self, 'DistributionId', value=distribution.distribution_id);

        # Route53 alias record for the CloudFront distribution
        apex_record= route53.ARecord(self, 'SiteAliasRecord',
          record_name=domain_name,
          target=route53.RecordTarget.from_alias(CloudFrontTarget(distribution)),
          zone=zone
        )

        # Route53 alias record for the CloudFront distribution
        route53.ARecord(self, 'WWWApexRecordAlias',
            record_name=f"www.{domain_name}",
            target=route53.RecordTarget.from_alias(Route53RecordTarget(apex_record)),
            zone=zone
        )

        # Deploy site contents to S3 bucket
        s3deploy.BucketDeployment(self, 'DeployWithInvalidation',
          sources=[s3deploy.Source.asset('./site-contents')],
          destination_bucket=site_bucket,
          distribution=distribution,
          distribution_paths=['/*']
        )
        
        alexa_assets = os.path.dirname(os.path.realpath(__file__)) + "/../skill"
        asset = assets.Asset(self, 'SkillAsset',
                             path=alexa_assets
                             )

        # role to access bucket
        role = Role(self, 'Role',
                    assumed_by=CompositePrincipal(
                        ServicePrincipal('alexa-appkit.amazon.com'),
                        ServicePrincipal('cloudformation.amazonaws.com')
                    )
                    )

        # Allow the skill resource to access the zipped skill package
        role.add_to_policy(PolicyStatement(
                           actions=['S3:GetObject'],
                           resources=[f'arn:aws:s3:::{asset.s3_bucket_name}/{asset.s3_object_key}']
                           )
                           )

        # DynamoDB Table
        house_table = dynamo_db.Table(self, 'HouseScore',
                                      partition_key=dynamo_db.Attribute(name='house', type=dynamo_db.AttributeType.STRING),
                                      billing_mode=dynamo_db.BillingMode.PAY_PER_REQUEST,
                                      removal_policy=RemovalPolicy.DESTROY
                                      )

        # install node dependencies for lambdas
        lambda_folder = os.path.dirname(os.path.realpath(__file__)) + "/../lambda_fns"
        subprocess.check_call("npm i".split(), cwd=lambda_folder, stdout=subprocess.DEVNULL)
        subprocess.check_call("npm run build".split(), cwd=lambda_folder, stdout=subprocess.DEVNULL)

        alexa_lambda = _lambda.Function(self, "AlexaLambdaHandler",
                                        runtime=_lambda.Runtime.NODEJS_14_X,
                                        code=_lambda.Code.from_asset("lambda_fns"),
                                        handler="lambda.handler",
                                        environment={
                                            "HOUSE_TABLE": house_table.table_name
                                        }
                                        )

        # grant the lambda role read/write permissions to our table
        house_table.grant_read_write_data(alexa_lambda)

        # create the skill
        skill = alexa_ask.CfnSkill(self, 'the-alexa-skill',
                                   vendor_id='M1EAIIJYKCP79N',
                                   authentication_configuration={
                                       'clientId': 'amzn1.application-oa2-client.845d94a637c448cb9fbc5d5141e9d18a',
                                       'clientSecret': 'c9648f1e0b740825fc92b72dcf97c25e36b682177871e8bc7da374c138b16f09',
                                       'refreshToken': 'Atzr|IwEBIFTK6WpPBOQ-CalUgo_NDJPV3VpEo7FCHNiEaHUk6D3ej6nQ0JJ-dESLgVxn7pHnH5yxjbBz-cbVCeM1jgZkvVgGhNa3OKQhk1MvGHoKfFW4La1rDlt97T3e4Wh9k8I1j_9g_luLSHyl9S_HKcn-QeoxGmNFR3Krg_2eGw2FUasWTiZI_MbPbZbbdiRAlPbaRqSYq3d6r4vfRGnIbpfb55SWZ1I8kTVCLPUnZEfLYL7Ksn0YeCb0dsT8RoUHJxW8vGZOnBaPgEbe-I6JckTI9SYx-pOY5jXFHO8RpB683mTToc67yAz1dnofeyIzc-Mgy03nSVF1lIXC4_VKdcm_oT0U_u35F5SRSKpmoTCB4Dr6Fb75I9cOJ9hCbJD96QgE0qhKNUjYWwQ9Zu0g7mHueK53LlS8syqpd4hnYs6QGO7sbXVqVa22mShmN09F-CDkDKLWnfCYSxKfGvb70F-H3s-b4yOB4yEbhxhsAlsZk-uHKYw-xpe02e-dbfwtRAXEM31ZmZDecBWs6axhRS_w_eWE86k3ltZo62FouonOCgOQmY9vriTZjEYrzGBscWL0IRw4X5VYJ697WsYIG1R6dAVs1ELBonPG267ZG8HYH7LIN3hbjlGRkBb1XoV4JHeVHIE'
                                   },
                                   skill_package={
                                       's3Bucket': asset.s3_bucket_name,
                                       's3Key': asset.s3_object_key,
                                       's3BucketRole': role.role_arn,
                                       'overrides': {
                                           'manifest': {
                                               'apis': {
                                                   'custom': {
                                                       'endpoint': {
                                                           'uri': alexa_lambda.function_arn
                                                       }
                                                   }
                                               }
                                           }
                                       }
                                   }
                                   )

        ###
        # Allow the Alexa service to invoke the fulfillment Lambda.
        # In order for the Skill to be created, the fulfillment Lambda
        # must have a permission allowing Alexa to invoke it, this causes
        # a circular dependency and requires the first deploy to allow all
        # Alexa skills to invoke the lambda, subsequent deploys will work
        # when specifying the eventSourceToken
        ###
        alexa_lambda.add_permission('AlexaPermission',
                                    # eventSourceToken: skill.ref,
                                    principal=ServicePrincipal('alexa-appkit.amazon.com'),
                                    action='lambda:InvokeFunction'
                                    )
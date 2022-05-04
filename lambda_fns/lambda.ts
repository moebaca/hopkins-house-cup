import {
  ErrorHandler,
  HandlerInput,
  RequestHandler,
  SkillBuilders,
  Skill,
  getSlotValue,
} from 'ask-sdk-core';
import {
  Response,
} from 'ask-sdk-model';
import * as ddbAdapter from 'ask-sdk-dynamodb-persistence-adapter';

const HOUSE_TABLE = process.env.HOUSE_TABLE || '';

const LaunchRequestHandler: RequestHandler = {
  canHandle(handlerInput: HandlerInput): boolean {
      return handlerInput.requestEnvelope.request.type === 'LaunchRequest' ||
      handlerInput.requestEnvelope.request.type === 'IntentRequest' &&
      handlerInput.requestEnvelope.request.intent.name === 'AMAZON.NavigateHomeIntent';
  },
  async handle(handlerInput: HandlerInput): Promise<Response> {
      const speechText = 'Cup speaking. Which house would you like me to give or take points from?';
      const repromptText = 'You can say things like, ten points to Ravenclaw, or fifty points from Slytherin.';
      const { attributesManager } = handlerInput;

      //   table.update_item(
      //     Key={'path': event['path']},
      //     UpdateExpression='ADD hits :incr',
      //     ExpressionAttributeValues={':incr': 1}
      // )
      console.log(attributesManager)
      const number = getSlotValue(handlerInput.requestEnvelope, 'number');
      const house = getSlotValue(handlerInput.requestEnvelope, 'house');

      attributesManager.setPersistentAttributes( {lastUpdatedDate: Date.now(), house: house, new_points: number, total_points: number, previous_point: number});
      await attributesManager.savePersistentAttributes();
      return handlerInput.responseBuilder
          .speak(speechText)
          .reprompt(repromptText)
          .withSimpleCard('Hopkins House Cup', speechText)
          .getResponse();
  },
};
const AddHousePointsIntentHandler: RequestHandler = {
  canHandle(handlerInput: HandlerInput): boolean {
      return handlerInput.requestEnvelope.request.type === 'IntentRequest' &&
          handlerInput.requestEnvelope.request.intent.name === 'AddHousePointsIntent';
  },
  async handle(handlerInput: HandlerInput): Promise<Response> {
      const { attributesManager } = handlerInput;
      const number = getSlotValue(handlerInput.requestEnvelope, 'number');
      const house = getSlotValue(handlerInput.requestEnvelope, 'house');
      const repromptText = 'You can say things like, ten points to Ravenclaw, or fifty points from Slytherin.';

      attributesManager.setPersistentAttributes( {lastUpdatedDate: Date.now(), house: house, new_points: number, total_points: number, previous_point: number});
      await attributesManager.savePersistentAttributes();

      const speechText = number + ' points have been awarded to ' + house + '!';

      return handlerInput.responseBuilder
          .speak(speechText)
          .reprompt(repromptText)
          .withSimpleCard(number + ' to ' + house, speechText)
          .getResponse();
  },
};
const ErrorHandler: ErrorHandler = {
  canHandle(handlerInput: HandlerInput, error: Error): boolean {
      return true;
  },
  handle(handlerInput: HandlerInput, error: Error): Response {
      console.log(`Error handled: ${error.message}`);

      return handlerInput.responseBuilder
          .speak('Sorry, I can\'t understand the command. Please say again.')
          .reprompt('Sorry, I can\'t understand the command. Please say again.')
          .getResponse();
  },
};

function getPersistenceAdapter(tableName: string) {
  return new ddbAdapter.DynamoDbPersistenceAdapter({
    tableName: tableName,
    partitionKeyName: "house"
  });
}
exports.handler = SkillBuilders.custom()
  .withPersistenceAdapter(getPersistenceAdapter(HOUSE_TABLE))
  .addRequestHandlers(
      LaunchRequestHandler,
      AddHousePointsIntentHandler,
  )
  .addErrorHandlers(ErrorHandler)
  .lambda();